from pathlib import Path
import os,json,csv,time,hashlib,cv2,torch
from PIL import Image,ImageOps,ImageDraw
from ultralytics import YOLO
from zone_counter import ZoneCounter

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');PH=ROOT/'phase2';OUT=PH/'results/external_counting';OUT.mkdir(parents=True,exist_ok=True)
sources=[PH/'data/mendeley_counting/extracted/Ground Truth/Toros.mp4']+sorted((PH/'data/mendeley_counting/extracted/Videos').glob('*.mp4'))
models={'generic':ROOT/'models/yolo26n.pt','pilot':ROOT/'results/detection_pilot/five_epoch_dev/weights/best.pt'}
expected={'generic':'9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef','pilot':'9b38f145a01585908fa9f1c44f3b00e4fb43f3cdf7f1fe2c8c387252ce47e81b'}
assert torch.cuda.is_available()
allrows=[]
for name,weights in models.items():
 digest=hashlib.sha256(weights.read_bytes()).hexdigest()
 if digest!=expected[name]:raise ValueError('Frozen checkpoint changed')
 for source in sources:
  model=YOLO(str(weights));cls=next(k for k,v in model.names.items() if v=='cow');dest=OUT/name/source.stem;dest.mkdir(parents=True,exist_ok=True)
  cap=cv2.VideoCapture(str(source));fps=cap.get(5);n=int(cap.get(7));w=int(cap.get(3));h=int(cap.get(4));counter=ZoneCounter();idx=0;events=[];tracks=[];detections=[];samples=[];t0=time.perf_counter();seen_frames=0
  writer=cv2.VideoWriter(str(dest/'annotated.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h))
  if not writer.isOpened():raise ValueError('VideoWriter unavailable')
  while True:
   ok,im=cap.read()
   if not ok:break
   result=model.track(im,persist=True,tracker='bytetrack.yaml',classes=[cls],imgsz=320,conf=.2,iou=.5,device=0,verbose=False)[0]
   positions={}
   if result.boxes is not None:
    boxes=result.boxes.xyxy.cpu().numpy();confs=result.boxes.conf.cpu().tolist();ids=result.boxes.id.int().cpu().tolist() if result.boxes.id is not None else [None]*len(boxes)
    for box,conf,tid in zip(boxes,confs,ids):
     x1,y1,x2,y2=map(float,box);cx=(x1+x2)/2/w;cy=(y1+y2)/2/h
     detections.append({'frame':idx,'time_s':idx/fps,'track_id':tid,'confidence':conf,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
     if tid is not None and .1<cy<.95:
      positions[tid]=cx;tracks.append({'frame':idx,'time_s':idx/fps,'track_id':tid,'axis_position':cx,'cy_norm':cy})
   for e in counter.update(idx/fps,positions):e['frame']=idx;events.append(e)
   if positions:seen_frames+=1
   vis=result.plot()
   for x in (.4,.6):cv2.line(vis,(int(w*x),0),(int(w*x),h),(0,220,255),2)
   cv2.putText(vis,f'{name} A->B {sum(e["direction"]=="A->B" for e in events)} B->A {sum(e["direction"]=="B->A" for e in events)}',(8,h-12),cv2.FONT_HERSHEY_SIMPLEX,.5,(0,255,0),2)
   writer.write(vis)
   if idx in {int(n*v) for v in [0,.1,.2,.3,.4,.5,.6,.7,.8,.9]}:samples.append((idx,Image.fromarray(cv2.cvtColor(vis,cv2.COLOR_BGR2RGB))))
   idx+=1
  cap.release();writer.release()
  for fn,rows,keys in [('events.csv',events,['time_s','track_id','direction','frame']),('tracks.csv',tracks,['frame','time_s','track_id','axis_position','cy_norm']),('detections.csv',detections,['frame','time_s','track_id','confidence','x1','y1','x2','y2'])]:
   with (dest/fn).open('w',newline='') as f:wr=csv.DictWriter(f,fieldnames=keys);wr.writeheader();wr.writerows(rows)
  sheet=Image.new('RGB',(5*360,2*250),'white');draw=ImageDraw.Draw(sheet)
  for i,(f,im) in enumerate(samples):
   x=i%5*360;y=i//5*250;sheet.paste(ImageOps.contain(im,(355,220)),(x,y));draw.text((x+3,y+223),f't={f/fps:.2f}s frame={f}',fill='black')
  sheet.save(dest/'contact.jpg',quality=90)
  row={'model':name,'model_sha256':digest,'video':source.stem,'source':str(source),'source_fps':fps,'source_frames':n,'processed_frames':idx,'tracked_frames':seen_frames,'unique_track_ids':len(counter.states),'A_to_B':sum(e['direction']=='A->B' for e in events),'B_to_A':sum(e['direction']=='B->A' for e in events),'events':events,'elapsed_s':time.perf_counter()-t0,'job_id':os.environ['SLURM_JOB_ID'],'input_size':320,'confidence':.2,'gate_axis':'x','gate_fraction':[.4,.6],'roi_y_fraction':[.1,.95],'stable_samples':3,'maximum_gap_s':2,'scope':'Frozen external inference before reference-based evaluation; no parameter tuning on these videos'}
  (dest/'summary.json').write_text(json.dumps(row,indent=2));allrows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='events'}),flush=True)
(OUT/'all_summaries.json').write_text(json.dumps(allrows,indent=2))
