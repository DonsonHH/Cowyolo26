from pathlib import Path
import cv2,os,json
from PIL import Image,ImageOps,ImageDraw
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'results/raw_multicam_review';OUT.mkdir(exist_ok=True)
p=ROOT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4';cap=cv2.VideoCapture(str(p));fps=cap.get(5);w=int(cap.get(3));h=int(cap.get(4))
# Preselected from source-only contact sheets; no tracking output determines these windows.
for start,end in [(390,420),(420,450),(450,480)]:
 sheet=Image.new('RGB',(10*180,3*355),'white');d=ImageDraw.Draw(sheet)
 for i,t in enumerate(range(start,end)):
  cap.set(cv2.CAP_PROP_POS_FRAMES,int(t*fps));ok,frame=cap.read()
  if not ok:continue
  crop=frame[:,int(.34*w):int(.75*w)]
  for y in [int(.4*h),int(.6*h)]:cv2.line(crop,(0,y),(crop.shape[1]-1,y),(0,220,255),3)
  im=Image.fromarray(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB));x=i%10*180;y=i//10*355;sheet.paste(ImageOps.contain(im,(175,325)),(x,y));d.text((x+2,y+328),f't={t}s',fill='black')
 sheet.save(OUT/f'raw_{start}_{end}.jpg',quality=92)
cap.release();(OUT/'scope.json').write_text(json.dumps({'job':os.environ['SLURM_JOB_ID'],'source':str(p),'windows_s':[[390,420],[420,450],[450,480]],'sample_interval_s':1,'images':'source frames with gate overlay, no predictions'}))
