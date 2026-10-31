from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,socket
import cv2,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='none'
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
board=ROOT/'board_delivery';prior=PROJECT/'pynq_periodic_joint_20261030/board_delivery'
s=load(board/'results/record.json');bg=board/'results/foreground_idle_identity/background';jobs=load(bg/'record.json')['jobs']
assert len(jobs)==11
out=ROOT/'results/media';out.mkdir(exist_ok=False)
fig,axes=plt.subplots(2,2,figsize=(13,9));records=[];bars=[];colors=['#8292a9','#ce8845','#94bcb3','#247c70']
sources=[(prior,'foreground_only','Earlier foreground'),(prior,'foreground_with_identity','Earlier direct background'),
         (board,'foreground_only','Current foreground'),(board,'foreground_idle_identity','Current idle background')]
for ci,(root,case,label) in enumerate(sources):
 rows=load(root/'results'/case/'timing_rows.json');values=np.full(392,np.nan)
 for r in rows:values[r['slot']]=r['release_to_count_ms']
 axes[0,0].plot(np.arange(392)/5,values,linewidth=.7,color=colors[ci],label=label)
 summary=next(r for r in load(root/'results/record.json')['cases'] if r['case']==case)
 records.append({'index':ci,'label':label,'case':case,'root':str(root),'slot':[r['slot'] for r in rows],
  'release_to_count_ms':[r['release_to_count_ms'] for r in rows],'processed':summary['processed_frames'],'skipped':summary['skipped_slots'],'late':summary['deadline_misses']})
 values=[summary['skipped_slots'],summary['deadline_misses']];rects=axes[0,1].bar(np.arange(2)+(ci-1.5)*.18,values,width=.16,color=colors[ci])
 for kind,value,b in zip(['Skipped','Late'],values,rects):
  axes[0,1].text(b.get_x()+b.get_width()/2,value+1.5,str(value),ha='center',fontsize=8)
  bars.append({'panel':1,'source_index':ci,'kind':kind,'value':value,'x':float(b.get_x()),'width':float(b.get_width())})
axes[0,0].axhline(200,linestyle='--',color='#ac5e68');axes[0,0].set_xlim(0,78.4);axes[0,0].set_ylim(0,470);axes[0,0].set_xlabel('Offered time / s');axes[0,0].set_ylabel('Release to count / ms');axes[0,0].set_title('All four runs retained; 392 offered slots each');axes[0,0].legend(fontsize=7,frameon=False)
axes[0,1].set_xticks([0,1],['Skipped frames','Over200ms']);axes[0,1].set_ylim(0,145);axes[0,1].set_xlim(-.6,1.6);axes[0,1].set_title('Single run per condition; all counts11 vs human12')
for mi,(key,label,color) in enumerate([('identity_network_process_CPU_ms','Actual network CPU','#247c70'),('actual_identity_network_ms','Elapsed including pauses','#ce8845')]):
 values=[r[key] for r in jobs];rects=axes[1,0].bar(np.arange(11)+(mi-.5)*.35,values,width=.32,label=label,color=color)
 for i,(value,b) in enumerate(zip(values,rects)):bars.append({'panel':2,'job_index':i,'key':key,'value':value,'x':float(b.get_x()),'width':float(b.get_width())})
axes[1,0].set_xticks(range(11),range(1,12));axes[1,0].set_ylim(0,1300);axes[1,0].set_xlim(-.6,10.6);axes[1,0].set_xlabel('Actual triggered job');axes[1,0].set_ylabel('ms');axes[1,0].set_title('Network continues across actual idle windows');axes[1,0].legend(fontsize=8,frameon=False)
pause=load(board/'results/foreground_idle_identity/worker_pause_intervals.json');case=next(r for r in s['cases'] if r['case']=='foreground_idle_identity');t0=case['clock_start_monotonic_ns']
windows=[((r['pause_acknowledged_monotonic_ns']-t0)/1e9,(r['foreground_completed_monotonic_ns']-r['pause_acknowledged_monotonic_ns'])/1e9) for r in pause]
netwindows=[((r['inference_finished_monotonic_ns']-round(r['actual_identity_network_ms']*1e6)-t0)/1e9,r['actual_identity_network_ms']/1000) for r in jobs]
axes[1,1].broken_barh(windows,(1.1,.65),facecolors='#247c70',label='Confirmed stopped during frontend')
axes[1,1].broken_barh(netwindows,(.1,.65),facecolors='#ce8845',label='Network elapsed spans (include pauses)')
axes[1,1].set_yticks([.4,1.4],['Identity network','Worker stopped']);axes[1,1].set_ylim(0,2.3);axes[1,1].set_xlim(0,max([78.4]+[a+b for a,b in netwindows])+1);axes[1,1].set_xlabel('Time since periodic release began / s');axes[1,1].set_title('All392 stop acknowledgements; 11 real networks');axes[1,1].legend(fontsize=7,frameon=False)
for axis in axes.flat:axis.spines[['top','right']].set_visible(False);axis.grid(axis='y',alpha=.12);axis.set_axisbelow(True)
fig.suptitle('PYNQ-Z2: idle-window background control on unchanged real models',fontsize=14)
fig.text(.055,.027,'Idle case392/392 at5FPS,28late; earlier direct case389/392,128late. Max queue grows from1.29s to27.60s.',fontsize=8)
fig.text(.055,.01,'Public image replay + simulated noRFID; no permanent identity truth. Longer network wall time includes suspension, not extra neural computation.',fontsize=8)
fig.subplots_adjust(left=.07,right=.985,top=.90,bottom=.10,hspace=.35,wspace=.30)
fig.savefig(out/'idle_control_all_runs.png',dpi=160);fig.savefig(out/'idle_control_all_runs.svg');plt.close(fig)
sheet=np.full((980,1600,3),(244,246,248),np.uint8);cv2.putText(sheet,'All11 actual idle-scheduled native photos: predictions only; no permanent identity ground truth',(12,30),cv2.FONT_HERSHEY_SIMPLEX,.63,(36,45,55),1,cv2.LINE_AA)
photos=[]
for i,job in enumerate(jobs):
 file=bg/job['photo_file'];assert sha(file)==job['photo_sha256'];image=cv2.imread(str(file));row,col=divmod(i,4);x=col*400;y=50+row*310
 scale=min(380/image.shape[1],220/image.shape[0]);small=cv2.resize(image,(max(1,round(image.shape[1]*scale)),max(1,round(image.shape[0]*scale))),interpolation=cv2.INTER_AREA)
 a=x+(400-small.shape[1])//2;b=y+(220-small.shape[0])//2;sheet[b:b+small.shape[0],a:a+small.shape[1]]=small
 status='ACCEPT' if job['accepted'] else 'REJECT';color=(35,115,60) if job['accepted'] else (60,70,80)
 cv2.putText(sheet,'f'+str(job['source_frame0'])+' track'+str(job['event']['track_id']),(x+10,y+242),cv2.FONT_HERSHEY_SIMPLEX,.55,(35,45,55),1,cv2.LINE_AA)
 cv2.putText(sheet,'pred '+job['predicted_id']+' sim '+format(job['similarity'],'.3f')+' '+status,(x+10,y+268),cv2.FONT_HERSHEY_SIMPLEX,.50,color,1,cv2.LINE_AA)
 photos.append({'index':i,'photo_file':job['photo_file'],'photo_sha256':sha(file),'source_frame0':job['source_frame0'],'predicted_id':job['predicted_id'],'similarity':job['similarity'],'accepted':job['accepted']})
assert cv2.imwrite(str(out/'all11_idle_photos.png'),sheet)
(out/'plot_data.json').write_text(json.dumps({'runs':records,'bars':bars,'worker_pause_windows_s':windows,'network_elapsed_windows_s':netwindows,'photos':photos},indent=2)+'\n')
summary={'status':'ALL_FOUR_RUNS392_PAUSE_WINDOWS_AND11_IDLE_PHOTOS_RENDERED','job_id':os.environ['SLURM_JOB_ID'],'numeric_panels':4,'photo_panels':11,
 'protocol_sha256':sha(ROOT/'protocol/media_v1.json'),'new_model_forwards':0,'whole_goal_complete':False}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()],indent=2)+'\n');print(json.dumps(summary),flush=True)
