from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,subprocess,os,socket
import cv2,numpy as np,matplotlib
matplotlib.use('Agg');import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='none'
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
p=load(ROOT/'protocol/media_v1.json');evalp=load(ROOT/'protocol/eval_v1.json')
quality=ROOT/'results/quality';board=ROOT/'board_delivery/results';s=load(board/'record.json');qs=load(quality/'summary.json')
assert s['actual_video_model_forwards']==2654 and s['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE'
out=ROOT/'results/media';out.mkdir(exist_ok=False)
barrows=[];fig,axes=plt.subplots(2,2,figsize=(12,8.5));colors=['#7a8ca7','#2a8a80','#ce8845']
def bars(axis,panel,x,values,width,color,labels):
 columns=axis.bar(x,values,width=width,color=color)
 for i,(b,value,label) in enumerate(zip(columns,values,labels)):
  axis.text(b.get_x()+b.get_width()/2,value+.18,str(round(float(value),2)),ha='center',fontsize=8)
  barrows.append({'panel':panel,'value':float(value),'bar_x':float(b.get_x()),'width':float(b.get_width()),'label':label})
source=[next(m['down'] for m in qs['video_metrics'] if m['scene']=='original' and m['mode']==mode and m['counter']=='handoff_events') for mode in ['FP32','QDQ']]
source.append(next(x['down'] for scene in s['scenes'] if scene['scene']=='original' for x in scene['metrics'] if x['counter']=='handoff_events'))
bars(axes[0,0],0,np.arange(3),source,.55,colors,['FP32','QDQ','O8 actual']);axes[0,0].set_xticks(range(3),['FP32','QDQ','O8 actual'])
axes[0,0].axhline(12,linestyle='--',color='#b75f66');axes[0,0].set_title('Development clip: down count (human total12)');axes[0,0].set_ylim(0,14);axes[0,0].set_xlim(-.6,2.6)
for i,(name,mode) in enumerate([('FP32','FP32'),('QDQ','QDQ'),('O8 actual','board')]):
 values=[]
 for stride in [6,1]:
  if mode!='board':row=next(m for m in qs['video_metrics'] if m['scene']=='toros' and m['mode']==mode and m['stride']==stride and m['counter']=='handoff_events');value=row['formal_event_metrics']['TP']
  else:
   scene=next(m for m in s['scenes'] if m['scene']=='toros');row=next(m for m in scene['metrics'] if m['stride']==stride and m['counter']=='handoff_events')
   formal=next(r for r in load(ROOT/'input/independent_board_verification.json')['publisher_event_scores'] if r['stride']==stride and r['counter']=='handoff_events');value=formal['TP']
  values.append(value)
 bars(axes[0,1],1,np.arange(2)+(i-1)*.23,values,.21,colors[i],[name+'5Hz',name+'30Hz'])
axes[0,1].set_xticks(range(2),['5Hz samples','30Hz samples']);axes[0,1].set_ylim(0,7);axes[0,1].set_xlim(-.6,1.6);axes[0,1].axhline(6,linestyle='--',color='#b75f66');axes[0,1].set_title('Toros: matched events of6 (FP0 in all)')
values=np.asarray([r['PNG_to_counter_with_raw_save_ms'] for r in s['rows']]);names=['Mean','P95','Maximum']
bars(axes[1,0],2,np.arange(3),[values.mean(),np.quantile(values,.95),values.max()],.55,['#2a8a80','#7a8ca7','#ce8845'],names)
axes[1,0].set_xticks(range(3),names);axes[1,0].set_ylim(0,float(np.ceil(values.max()/50)*50+50));axes[1,0].set_xlim(-.6,2.6);axes[1,0].axhline(200,linestyle='--',color='#b75f66');axes[1,0].set_ylabel('ms');axes[1,0].set_title('PNG to counter+raw save:'+str(int((values>200).sum()))+'/2654 over200ms')
stages=['PNG_read_ms','preprocess_ms','input_hash_check_ms','tensor_to_raw_ms','decode_restore_ms','tracker_counter_ms','raw_memorymap_and_row_save_ms']
means=[np.mean([r[k] for r in s['rows']]) for k in stages]
axis=axes[1,1];columns=axis.barh(np.arange(7),means,color=['#7a8ca7']*3+['#2a8a80']+['#ce8845']*3)
for i,(b,v,key) in enumerate(zip(columns,means,stages)):
 axis.text(v+.8,b.get_y()+b.get_height()/2,str(round(float(v),2)),va='center',fontsize=8)
 barrows.append({'panel':3,'horizontal':True,'value':float(v),'bar_y':float(b.get_y()),'height':float(b.get_height()),'label':key})
axis.set_yticks(range(7),['PNG read','Preprocess','Input hash','Actual O8 model','Decode+restore','Track+count','Raw save']);axis.invert_yaxis();axis.set_xlim(0,175);axis.set_ylim(6.6,-.6);axis.set_xlabel('Mean ms');axis.set_title('All2654 actual board frames; no identity load')
for a in axes.flat:a.spines[['top','right']].set_visible(False);a.grid(axis='x' if a==axis else 'y',alpha=.12);a.set_axisbelow(True)
fig.suptitle('Mosaic0.5 seed26 fixed192: FP32, QDQ and actual PYNQ-Z2 O8',fontsize=15)
fig.text(.05,.025,'Prepared lossless192inputs; unpaced board replay. Human12 is total-only; Toros6 has publisher-derived events.',fontsize=8)
fig.text(.05,.009,'Source used for development; no livecamera, periodic deadline guarantee or simultaneous identity claim.',fontsize=8)
fig.subplots_adjust(left=.06,right=.985,top=.90,bottom=.10,hspace=.38,wspace=.65)
fig.savefig(out/'quality_and_actual_board.png',dpi=160);fig.savefig(out/'quality_and_actual_board.svg');plt.close(fig)
save={'bars':barrows,'panels':4,'source_down_counts':source,'timing_ymax':float(np.ceil(values.max()/50)*50+50),'timing_total_ms':{'mean':float(values.mean()),'p95':float(np.quantile(values,.95)),'max':float(values.max())}}
(out/'plot_data.json').write_text(json.dumps(save,indent=2)+'\n')
cases=[]
for name,folder in [('FP32 ORT',quality/'original/FP32'),('INT8 QDQ ORT',quality/'original/QDQ'),('Actual PYNQ O8',board/'original')]:
 trace=gz(folder/'stride5_counter_trace.json.gz');byframe=defaultdict(list)
 for row in trace['post_tracker']:byframe[row['frame0']].append(row)
 events=[e for e in trace['handoff_events'] if 8912<=e['frame0']<=10873]
 cases.append({'name':name,'boxes':byframe,'events':events})
ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg';movie=out/'FP32_QDQ_actual_PYNQ_8912_10873.mp4'
log=(out/'encode.log').open('xb');process=subprocess.Popen([ffmpeg,'-nostdin','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s','1920x450','-r','25','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','22','-pix_fmt','yuv420p','-threads','1','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE,stderr=log)
source=evalp['videos'][0];assert sha(source['path'])==source['sha256'];cap=cv2.VideoCapture(source['path']);previews=[];count=0
try:
 for frame in range(10874):
  ok,native=cap.read();assert ok and native.shape==(1440,2560,3)
  if frame<8912:continue
  canvas=np.full((450,1920,3),(24,32,44),np.uint8);sample=frame-frame%5
  cv2.putText(canvas,'Mosaic0.5 seed26 actual O8: source f'+str(frame)+'; held5Hz sample f'+str(sample)+';25fps playback; human total12',(10,22),cv2.FONT_HERSHEY_SIMPLEX,.62,(240,244,248),1,cv2.LINE_AA)
  cv2.putText(canvas,'Same source context below, not actual network input. Actual O8 was unpaced PNG replay; stable5Hz and identity concurrency not proven.',(10,47),cv2.FONT_HERSHEY_SIMPLEX,.57,(220,228,238),1,cv2.LINE_AA)
  previewrows=[]
  for i,case in enumerate(cases):
   tile=cv2.resize(native,(640,360),interpolation=cv2.INTER_AREA)
   for x in [.34,.75]:cv2.line(tile,(round(640*x),0),(round(640*x),359),(0,184,255),1)
   for y in [.4,.6]:cv2.line(tile,(round(640*.34),round(360*y)),(round(640*.75),round(360*y)),(0,184,255),1)
   for row in case['boxes'][sample]:
    a,b,c,d=[round(v/4) for v in row['xyxy']];cv2.rectangle(tile,(a,b),(c,d),(100,235,156),1)
    cv2.putText(tile,str(row['track_id']) if row['track_id'] is not None else '?',(a,max(36,b-2)),cv2.FONT_HERSHEY_SIMPLEX,.4,(100,235,156),1)
   down=sum(e['direction']=='A->B' and e['frame0']<=frame for e in case['events']);up=sum(e['direction']=='B->A' and e['frame0']<=frame for e in case['events'])
   canvas[70:430,i*640:(i+1)*640]=tile
   cv2.putText(canvas,case['name']+' / down '+str(down)+' up '+str(up),(i*640+8,66),cv2.FONT_HERSHEY_SIMPLEX,.55,(240,244,248),1,cv2.LINE_AA)
   previewrows.append({'mode_index':i,'sample_frame0':sample,'down':down,'up':up,'post_tracker_boxes':len(case['boxes'][sample])})
  process.stdin.write(canvas.tobytes());count+=1
  if frame in p['source_anchor_frames']:
   file=out/('source_f'+str(frame)+'.png');assert cv2.imwrite(str(file),canvas)
   previews.append({'source_frame0':frame,'video_index0':frame-8912,'file':file.relative_to(ROOT).as_posix(),'sha256':sha(file),'panels':previewrows})
 process.stdin.close();assert process.wait(timeout=60)==0;log.close();cap.release();assert count==1962
except BaseException:
 cap.release()
 if process.poll() is None:process.terminate()
 log.close();raise
meta={'status':'ACTUAL_BOARD_THREE_COLUMN_VIDEO_AND_FOUR_PANEL_FIGURE_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
 'protocol_sha256':sha(ROOT/'protocol/media_v1.json'),'movie_file':movie.relative_to(ROOT).as_posix(),'movie_sha256':sha(movie),
 'frames':count,'dimensions_WH':[1920,450],'playback_fps':25,'source_decode_frames':10874,'scope_frame0_inclusive':[8912,10873],
 'previews':previews,'figure_panels':4,'preview_panels':12,'new_network_forwards':0,'whole_goal_complete':False}
(out/'media_metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()],indent=2)+'\n')
print(json.dumps({k:v for k,v in meta.items() if k!='previews'}),flush=True)
