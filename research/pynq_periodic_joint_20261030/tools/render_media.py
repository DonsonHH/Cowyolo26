from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,socket,math
import cv2,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='none'
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
p=load(ROOT/'protocol/media_v1.json');board=ROOT/'board_delivery';s=load(board/'results/record.json');bg=board/'results/foreground_with_identity/background';jobs=load(bg/'record.json')['jobs']
assert len(s['cases'])==2 and len(jobs)==11
out=ROOT/'results/media';out.mkdir(exist_ok=False);cells=[];photo_manifest=[]
sheet=np.full((980,1600,3),(244,246,248),np.uint8)
cv2.putText(sheet,'All11 actual count-triggered native photos: provisional retrieval, no identity ground truth',(12,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(36,45,55),1,cv2.LINE_AA)
for i,job in enumerate(jobs):
 file=bg/job['photo_file'];assert sha(file)==job['photo_sha256'];image=cv2.imread(str(file));assert image is not None
 row,col=divmod(i,4);x=col*400;y=50+row*310
 scale=min(380/image.shape[1],220/image.shape[0]);small=cv2.resize(image,(max(1,round(image.shape[1]*scale)),max(1,round(image.shape[0]*scale))),interpolation=cv2.INTER_AREA)
 left=x+(400-small.shape[1])//2;top=y+(220-small.shape[0])//2;sheet[top:top+small.shape[0],left:left+small.shape[1]]=small
 status='ACCEPT' if job['accepted'] else 'REJECT';color=(35,115,60) if job['accepted'] else (60,70,80)
 cv2.putText(sheet,'f'+str(job['source_frame0'])+' track'+str(job['event']['track_id']),(x+12,y+242),cv2.FONT_HERSHEY_SIMPLEX,.56,(35,45,55),1,cv2.LINE_AA)
 cv2.putText(sheet,'pred '+job['predicted_id']+' sim '+format(job['similarity'],'.3f')+' '+status,(x+12,y+268),cv2.FONT_HERSHEY_SIMPLEX,.51,color,1,cv2.LINE_AA)
 photo_manifest.append({'index':i,'frame0':job['source_frame0'],'photo_file':job['photo_file'],'photo_sha256':sha(file),
  'cell_xywh':[x,y,400,310],'display_xywh':[left,top,small.shape[1],small.shape[0]],'predicted_id':job['predicted_id'],'similarity':job['similarity'],'accepted':job['accepted'],'identity_GT_available':False})
photo=out/'all11_actual_photos.png';assert cv2.imwrite(str(photo),sheet)
fig,axes=plt.subplots(2,2,figsize=(14,10));axis=axes[0,0];lines=[];bars=[]
colors=['#2a8a80','#cd8848']
for ci,case in enumerate(['foreground_only','foreground_with_identity']):
 rows=load(board/'results'/case/'timing_rows.json');latency=np.full(392,np.nan)
 for row in rows:latency[row['slot']]=row['release_to_count_ms']
 axis.plot(np.arange(392)/5,latency,color=colors[ci],linewidth=.8,label=['Foreground only','Foreground + actual identity'][ci])
 lines.append({'case':case,'slot':[r['slot'] for r in rows],'release_to_count_ms':[r['release_to_count_ms'] for r in rows]})
axis.axhline(200,linestyle='--',color='#a75a67');axis.set_xlim(0,78.4);axis.set_ylim(0,450);axis.set_xlabel('Offered release time / s');axis.set_ylabel('Release to count / ms');axis.set_title('All392 offered slots; gaps are skipped');axis.legend(fontsize=8,frameon=False)
axis=axes[0,1];labels=['Processed','Skipped','Over200ms']
for ci,case in enumerate(s['cases']):
 values=[case['processed_frames'],case['skipped_slots'],case['deadline_misses']];rects=axis.bar(np.arange(3)+(ci-.5)*.32,values,width=.29,color=colors[ci])
 for label,value,b in zip(labels,values,rects):
  axis.text(b.get_x()+b.get_width()/2,value+5,str(value),ha='center',fontsize=9)
  bars.append({'panel':1,'case':case['case'],'label':label,'value':value,'x':float(b.get_x()),'width':float(b.get_width())})
axis.set_xticks(range(3),labels);axis.set_xlim(-.6,2.6);axis.set_ylim(0,450);axis.set_title('Same11 down events; human total12')
axis=axes[1,0];bottom=np.zeros(11);stages=['queue_wait_ms','highres_JPEG_read_ms','runtime_native_crop_and_photo_save_ms','Pillow_preprocess_ms','actual_identity_network_ms']
stage_labels=['Queue','Highres read','Crop + PNG save','Preprocess','Actual encoder'];palette=['#8795ab','#b8c1ce','#d49b68','#85b5aa','#297f75']
for stage,label,color in zip(stages,stage_labels,palette):
 values=np.asarray([j[stage] for j in jobs]);rects=axis.bar(np.arange(11),values,bottom=bottom,width=.72,label=label,color=color)
 for i,(value,b) in enumerate(zip(values,rects)):bars.append({'panel':2,'job_index':i,'stage':stage,'value':float(value),'bottom':float(bottom[i]),'x':float(b.get_x()),'width':float(b.get_width())})
 bottom+=values
axis.set_xticks(range(11),[str(i+1) for i in range(11)]);axis.set_xlim(-.6,10.6);axis.set_ylim(0,3200);axis.set_xlabel('Actual triggered identity job');axis.set_ylabel('ms');axis.set_title('All11 actual jobs: queue and computation');axis.legend(fontsize=7,ncol=3,frameon=False)
axes[1,1].imshow(cv2.cvtColor(sheet,cv2.COLOR_BGR2RGB));axes[1,1].axis('off');axes[1,1].set_title('All native crops; only1 passes fixed threshold')
for axis in axes.flat:
 axis.spines[['top','right']].set_visible(False)
 if axis!=axes[1,1]:axis.grid(axis='y',alpha=.13);axis.set_axisbelow(True)
fig.suptitle('PYNQ-Z2 O8 frontend + actual ARM identity: fixed5Hz periodic replay',fontsize=15)
fig.text(.04,.025,'Prepared192framebank and same-frame1050x1440JPEG replay; simulated noRFID. Actual networks, crops and retrieval all on same board.',fontsize=8)
fig.text(.04,.009,'78.4s per case; one run each. Approx5FPS throughput is separate from200ms deadlines and identity accuracy. No livecamera / RFID claim.',fontsize=8)
fig.subplots_adjust(left=.06,right=.99,top=.91,bottom=.09,hspace=.34,wspace=.27)
fig.savefig(out/'periodic_and_identity.png',dpi=150);fig.savefig(out/'periodic_and_identity.svg');plt.close(fig)
(out/'plot_data.json').write_text(json.dumps({'lines':lines,'bars':bars,'photo_panels':photo_manifest,'figure_panels':4,'standalone_photo_panels':11},indent=2)+'\n')
record={'status':'ALL_PERIODIC_RELEASES_AND_ALL11_TRIGGERED_PHOTOS_RENDERED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/media_v1.json'),'numeric_figure_panels':4,
 'standalone_photo_panels':11,'all_photo_sha256':sha(photo),'new_model_forwards':0,'whole_goal_complete':False}
(out/'summary.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()],indent=2)+'\n')
print(json.dumps(record),flush=True)
