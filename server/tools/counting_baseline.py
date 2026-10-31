"""Development-only YOLO26n/ByteTrack two-zone counting on downloaded videos."""
from pathlib import Path
import os,json,csv,time,hashlib
import numpy as np,cv2,torch
from PIL import Image,ImageOps,ImageDraw
from ultralytics import YOLO

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026')
OUT=ROOT/'results'/os.environ.get('IDCOO_COUNT_OUTPUT','counting_dev');OUT.mkdir(parents=True,exist_ok=True)
assert torch.cuda.is_available(),'GPU allocation required for this baseline'
weights=Path(os.environ.get('IDCOO_MODEL_PATH',str(ROOT/'models/yolo26n.pt')))
model=YOLO(str(weights));cow_class=next(k for k,v in model.names.items() if v=='cow')
paths=sorted(p for p in (ROOT/'data/cows2021_samples').glob('*/RGB.avi'))
mc=sorted((ROOT/'data/multicam_samples').rglob('*.mp4'))
if mc:paths.extend(mc[:1])
summaries=[]
for path in paths:
 name=path.parent.name if path.name=='RGB.avi' else path.parent.name+'_'+path.stem
 out=OUT/name;out.mkdir(exist_ok=True)
 cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);w=int(cap.get(3));h=int(cap.get(4));total=int(cap.get(7))
 # Fixed development gate. Its relation to the physical farm direction is not known.
 left=.40*w;right=.60*w
 writer=cv2.VideoWriter(str(out/'annotated.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
 state={};events=[];boxes=[];tiles=[];frame_idx=0;t0=time.perf_counter();cow_frames=0
 # Reset tracking session for each independent source video.
 if getattr(model,'predictor',None) is not None and hasattr(model.predictor,'trackers'):
  for tr in model.predictor.trackers:tr.reset()
 max_frames=min(total,900) if path.suffix=='.mp4' else total
 while frame_idx<max_frames:
  ok,frame=cap.read()
  if not ok:break
  result=model.track(frame,persist=True,tracker='bytetrack.yaml',classes=[cow_class],imgsz=320,conf=.20,iou=.5,device=0,verbose=False)[0]
  n=0
  if result.boxes is not None and result.boxes.id is not None:
   for xyxy,tid,conf in zip(result.boxes.xyxy.cpu().numpy(),result.boxes.id.int().cpu().tolist(),result.boxes.conf.cpu().tolist()):
    x1,y1,x2,y2=map(float,xyxy);cx=(x1+x2)/2;cy=(y1+y2)/2;n+=1
    region='A' if cx<left else ('B' if cx>right else 'MID')
    rec=state.setdefault(tid,{'stable':None,'candidate':None,'streak':0,'first_frame':frame_idx})
    if region!='MID':
     if rec['candidate']==region:rec['streak']+=1
     else:rec['candidate']=region;rec['streak']=1
     if rec['streak']>=3 and rec['stable']!=region:
      previous=rec['stable'];rec['stable']=region
      if previous is not None:events.append({'frame':frame_idx,'time_s':frame_idx/fps,'track_id':tid,'direction':previous+'->'+region})
    else:rec['candidate']=None;rec['streak']=0
    boxes.append({'frame':frame_idx,'time_s':frame_idx/fps,'track_id':tid,'confidence':conf,'x1':x1,'y1':y1,'x2':x2,'y2':y2,'zone':region})
  if n:cow_frames+=1
  annotated=result.plot()
  cv2.line(annotated,(int(left),0),(int(left),h),(0,220,255),2);cv2.line(annotated,(int(right),0),(int(right),h),(0,220,255),2)
  cv2.putText(annotated,f'DEV A->B {sum(e["direction"]=="A->B" for e in events)} B->A {sum(e["direction"]=="B->A" for e in events)} frame {frame_idx}',(15,h-18),cv2.FONT_HERSHEY_SIMPLEX,.6,(0,255,0),2)
  writer.write(annotated)
  if frame_idx%max(1,max_frames//12)==0 and len(tiles)<12:tiles.append((frame_idx,Image.fromarray(cv2.cvtColor(annotated,cv2.COLOR_BGR2RGB))))
  frame_idx+=1
 cap.release();writer.release();elapsed=time.perf_counter()-t0
 for fn,rows in [('tracks.csv',boxes),('predicted_events.csv',events)]:
  with (out/fn).open('w',newline='') as f:
   keys=list(rows[0]) if rows else (['frame','time_s','track_id','direction'] if fn.startswith('predicted') else ['frame','time_s','track_id','confidence','x1','y1','x2','y2','zone'])
   writer_csv=csv.DictWriter(f,fieldnames=keys);writer_csv.writeheader();writer_csv.writerows(rows)
 sheet=Image.new('RGB',(4*360,3*225),'white');draw=ImageDraw.Draw(sheet)
 for i,(idx,im) in enumerate(tiles):sheet.paste(ImageOps.contain(im,(355,200)),((i%4)*360,(i//4)*225));draw.text(((i%4)*360+3,(i//4)*225+202),f'frame={idx} t={idx/fps:.2f}s',fill='black')
 sheet.save(out/'contact_sheet.jpg',quality=90)
 summary={'source':str(path),'job':os.environ['SLURM_JOB_ID'],'gpu':torch.cuda.get_device_name(0),'source_fps':fps,'source_frames':total,'processed_frames':frame_idx,'processed_duration_s':frame_idx/fps,'cow_tracked_frames':cow_frames,'unique_track_ids':len(state),'A_to_B':sum(e['direction']=='A->B' for e in events),'B_to_A':sum(e['direction']=='B->A' for e in events),'elapsed_s':elapsed,'scope':'development prediction; no ground-truth accuracy claim; arbitrary A/B gate','gate_fractions':[.4,.6],'model_path':str(weights),'model_sha256':hashlib.sha256(weights.read_bytes()).hexdigest(),'imgsz':320}
 (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8');summaries.append(summary);print(json.dumps(summary),flush=True)
(OUT/'all_summaries.json').write_text(json.dumps(summaries,indent=2),encoding='utf8')
