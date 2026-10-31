from pathlib import Path
import os,json,cv2,numpy as np
from PIL import Image,ImageOps,ImageDraw
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2');SRC=ROOT/'data/mendeley_counting/extracted/Ground Truth';OUT=ROOT/'results/reference_review';OUT.mkdir(parents=True,exist_ok=True)
ref=json.loads((ROOT/'results/author_gt_audit/summary.json').read_text())['events'];gt=np.loadtxt(SRC/'gt.txt',delimiter=',',ndmin=2)
c=cv2.VideoCapture(str(SRC/'Toros.mp4'));fps=c.get(5);sheet=Image.new('RGB',(3*520,6*320),'white');d=ImageDraw.Draw(sheet)
for i,e in enumerate(ref):
 tid=e['track_id'];center=e['frame']
 for j,frame in enumerate([center-12,center,center+12]):
  c.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,im=c.read()
  if not ok:continue
  for r in gt[(gt[:,0]==frame)&(gt[:,1]==tid)]:
   x,y,w,h=map(int,r[2:6]);cv2.rectangle(im,(x,y),(x+w,y+h),(0,255,0),3);cv2.putText(im,f'author ID{tid}',(max(0,x),max(20,y-10)),cv2.FONT_HERSHEY_SIMPLEX,1,(0,255,0),2)
  for p in (.4,.6):cv2.line(im,(int(p*1920),0),(int(p*1920),1080),(0,220,255),3)
  image=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));x=j*520;y=i*320;sheet.paste(ImageOps.contain(image,(515,290)),(x,y));d.text((x+3,y+292),f'ref ID{tid} f={frame} t={frame/fps:.3f}s',fill='black')
c.release();sheet.save(OUT/'six_reference_passages.jpg',quality=93)
(OUT/'scope.json').write_text(json.dumps({'job':os.environ['SLURM_JOB_ID'],'reference_authority':'publisher trajectories','source_unchanged':True,'reference_events':len(ref),'note':'Publisher-ID overlays only; no model predictions. Reference time is stable destination completion, not center-line crossing time.'}))
