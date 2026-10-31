from pathlib import Path
from collections import defaultdict,Counter
import os,json,csv,cv2,numpy as np
from PIL import Image,ImageOps,ImageDraw
from zone_counter import ZoneCounter
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2');SRC=ROOT/'data/mendeley_counting/extracted';OUT=ROOT/'results/author_gt_audit';OUT.mkdir(parents=True,exist_ok=True)
raw=np.loadtxt(SRC/'Ground Truth/gt.txt',delimiter=',',ndmin=2)
cap=cv2.VideoCapture(str(SRC/'Ground Truth/Toros.mp4'));fps=cap.get(5);n=int(cap.get(7));w=int(cap.get(3));h=int(cap.get(4));byframe=defaultdict(list);byid=defaultdict(list)
for row in raw:byframe[int(row[0])].append(row);byid[int(row[1])].append(row)
duplicates=[{'frame':f,'track_id':t,'count':c} for (f,t),c in Counter((int(r[0]),int(r[1])) for r in raw).items() if c>1]
invalid=[r.tolist() for r in raw if not (0<=r[0]<n and r[4]>0 and r[5]>0 and np.isfinite(r).all())]
outside=[r.tolist() for r in raw if min(r[2],r[3])<0 or r[2]+r[4]>w+1 or r[3]+r[5]>h+1]
counter=ZoneCounter();events=[];positions=[]
for frame in range(n):
 pos={int(r[1]):float((r[2]+r[4]/2)/w) for r in byframe[frame] if .1<(r[3]+r[5]/2)/h<.95}
 for e in counter.update(frame/fps,pos):e.update(frame=frame);events.append(e)
 for tid,p in pos.items():positions.append({'frame':frame,'time_s':frame/fps,'track_id':tid,'axis_position':p})
tracks=[]
for tid,rows in sorted(byid.items()):
 arr=np.array(sorted(rows,key=lambda r:r[0]));gaps=np.diff(arr[:,0]);cx=(arr[:,2]+arr[:,4]/2)/w;cy=(arr[:,3]+arr[:,5]/2)/h
 tracks.append({'track_id':tid,'rows':len(rows),'first_frame':int(arr[0,0]),'last_frame':int(arr[-1,0]),'max_gap_frames':float(gaps.max()) if len(gaps) else 0,'first_center':[float(cx[0]),float(cy[0])],'last_center':[float(cx[-1]),float(cy[-1])],'delta_center_x':float(cx[-1]-cx[0]),'max_center_jump_pixels':float(np.max(np.hypot(np.diff(cx)*w,np.diff(cy)*h))) if len(cx)>1 else 0})
for page,frames in enumerate(([0,60,120,180,240,300,360,420,478],)):
 sheet=Image.new('RGB',(3*640,3*390),'white');d=ImageDraw.Draw(sheet)
 for i,frame in enumerate(frames):
  cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,im=cap.read()
  if not ok:continue
  for r in byframe[frame]:
   x,y,ww,hh=map(int,r[2:6]);tid=int(r[1]);cv2.rectangle(im,(x,y),(x+ww,y+hh),(0,255,0),3);cv2.putText(im,f'author ID {tid}',(x,max(20,y-5)),cv2.FONT_HERSHEY_SIMPLEX,.8,(0,255,0),2)
  for xx in (.4,.6):cv2.line(im,(int(xx*w),0),(int(xx*w),h),(0,220,255),2)
  image=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));x=i%3*640;y=i//3*390;sheet.paste(ImageOps.contain(image,(635,355)),(x,y));d.text((x+3,y+358),f'frame={frame} source zero based',fill='black')
 sheet.save(OUT/'author_gt_overlay.jpg',quality=92)
cap.release()
summary={'job_id':os.environ['SLURM_JOB_ID'],'source_frame_base':0,'video_frames':n,'fps':fps,'gt_rows':len(raw),'unique_id_values':len(byid),'duplicate_frame_ids':duplicates,'invalid_rows':invalid,'outside_image_rows':len(outside),'tracks':tracks,'events':events,'scope':'events derived from publisher trajectories using predefined two-zone rule, not publisher event-count labels; GT quality findings retained'}
(OUT/'summary.json').write_text(json.dumps(summary,indent=2))
with (OUT/'reference_events.csv').open('w',newline='') as f:
 wr=csv.DictWriter(f,fieldnames=['time_s','track_id','direction','frame']);wr.writeheader();wr.writerows(events)
print(json.dumps(summary),flush=True)
