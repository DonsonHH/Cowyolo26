"""Development baseline on the full downloaded MultiCam passage video.
The ROI/axis are derived from the raw camera view, without using prediction counts.
"""
from pathlib import Path
import os,json,csv,time,cv2,torch,numpy as np,hashlib
from PIL import Image,ImageOps,ImageDraw
from ultralytics import YOLO
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'results'/os.environ.get('IDCOO_MC_OUTPUT','multicam_count_dev');OUT.mkdir(parents=True,exist_ok=True)
source=ROOT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4'
weights=Path(os.environ.get('IDCOO_MODEL_PATH',str(ROOT/'models/yolo26n.pt')))
model=YOLO(str(weights));cow_class=next(k for k,v in model.names.items() if v=='cow')
cap=cv2.VideoCapture(str(source));fps=cap.get(5);w=int(cap.get(3));h=int(cap.get(4));total=int(cap.get(7));stride=5;eff_fps=fps/stride
xlo,xhi=.34*w,.75*w;upper,lower=.4*h,.6*h
writer=cv2.VideoWriter(str(OUT/'annotated.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),eff_fps,(1280,720))
state={};events=[];tracks=[];frames=[];sampled=0;idx=0;start=time.perf_counter();in_roi_frames=0
while True:
 ok,frame=cap.read()
 if not ok:break
 if idx%stride:idx+=1;continue
 r=model.track(frame,persist=True,tracker='bytetrack.yaml',classes=[cow_class],imgsz=320,conf=.20,iou=.5,device=0,verbose=False)[0]
 active=set();n=0
 if r.boxes is not None and r.boxes.id is not None:
  for box,tid,conf in zip(r.boxes.xyxy.cpu().numpy(),r.boxes.id.int().cpu().tolist(),r.boxes.conf.cpu().tolist()):
   x1,y1,x2,y2=map(float,box);cx=(x1+x2)/2;cy=(y1+y2)/2
   if not xlo<cx<xhi:continue
   active.add(tid);n+=1;zone='A' if cy<upper else ('B' if cy>lower else 'MID')
   rec=state.setdefault(tid,{'stable':None,'candidate':None,'streak':0,'last_seen':sampled})
   if sampled-rec['last_seen']>10:rec.update(stable=None,candidate=None,streak=0)
   rec['last_seen']=sampled
   if zone=='MID':rec.update(candidate=None,streak=0)
   else:
    rec['streak']=rec['streak']+1 if rec['candidate']==zone else 1;rec['candidate']=zone
    if rec['streak']>=3 and rec['stable']!=zone:
     previous=rec['stable'];rec['stable']=zone
     if previous:events.append({'source_frame':idx,'time_s':idx/fps,'track_id':tid,'direction':previous+'->'+zone})
   tracks.append({'source_frame':idx,'time_s':idx/fps,'track_id':tid,'confidence':conf,'x1':x1,'y1':y1,'x2':x2,'y2':y2,'zone':zone})
 for tid,rec in state.items():
  if tid not in active:rec.update(candidate=None,streak=0)
 if n:in_roi_frames+=1
 annotated=r.plot();cv2.rectangle(annotated,(int(xlo),0),(int(xhi),h),(255,0,255),3)
 for yy in (upper,lower):cv2.line(annotated,(int(xlo),int(yy)),(int(xhi),int(yy)),(0,220,255),3)
 countA=sum(e['direction']=='A->B' for e in events);countB=len(events)-countA
 cv2.putText(annotated,f'DEV Top->Bottom {countA} Bottom->Top {countB} t={idx/fps:.1f}s',(70,h-35),cv2.FONT_HERSHEY_SIMPLEX,1.2,(0,255,0),3)
 writer.write(cv2.resize(annotated,(1280,720)))
 if n and len(frames)<36 and (not frames or idx-frames[-1][0]>=250):frames.append((idx,Image.fromarray(cv2.cvtColor(annotated,cv2.COLOR_BGR2RGB))))
 sampled+=1;idx+=1
 if sampled%300==0:print(json.dumps({'sampled':sampled,'source_time_s':idx/fps,'A_to_B':countA,'B_to_A':countB}),flush=True)
cap.release();writer.release()
for name,rows,keys in [('tracks.csv',tracks,['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','zone']),('predicted_events.csv',events,['source_frame','time_s','track_id','direction'])]:
 with (OUT/name).open('w',newline='') as f:ww=csv.DictWriter(f,fieldnames=keys);ww.writeheader();ww.writerows(rows)
for page in range((len(frames)+11)//12):
 sheet=Image.new('RGB',(4*360,3*225),'white');draw=ImageDraw.Draw(sheet)
 for j,(f,im) in enumerate(frames[page*12:page*12+12]):
  x=j%4*360;y=j//4*225;sheet.paste(ImageOps.contain(im,(355,200)),(x,y));draw.text((x+3,y+202),f't={f/fps:.2f}s',fill='black')
 sheet.save(OUT/f'active_contact_{page+1}.jpg',quality=90)
summary={'source':str(source),'job_id':os.environ['SLURM_JOB_ID'],'gpu':torch.cuda.get_device_name(0),'processed_source_frames':idx,'sampled_frames':sampled,'source_fps':fps,'effective_detection_fps':eff_fps,'source_duration_s':idx/fps,'input_size':320,'cow_class':cow_class,'roi_x_fraction':[.34,.75],'gate_axis':'y','gate_fraction':[.4,.6],'stability_samples':3,'A_to_B':sum(e['direction']=='A->B' for e in events),'B_to_A':sum(e['direction']=='B->A' for e in events),'cow_tracked_in_roi_frames':in_roi_frames,'elapsed_s':time.perf_counter()-start,'model_path':str(weights),'model_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'scope':'development-only prediction, geometry from raw view; ground-truth review required; no bidirectional/accuracy claim from predicted events'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');print(json.dumps(summary),flush=True)
