from pathlib import Path
import cv2,os,json
from PIL import Image,ImageOps,ImageDraw
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'phase2/results/source_refine';OUT.mkdir(parents=True,exist_ok=True)
cap=cv2.VideoCapture(str(ROOT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4'));fps=cap.get(5);w=int(cap.get(3));h=int(cap.get(4))
for name,times in [('overlap',list(range(366,390))),('thresholds',[358,359,360,364,365,366,369,370,371,372,373,374,375,376,377,378,379,380,383,384,385,386,387,388])]:
 for page in range((len(times)+11)//12):
  sheet=Image.new('RGB',(4*400,3*560),'white');d=ImageDraw.Draw(sheet)
  for i,t in enumerate(times[page*12:page*12+12]):
   cap.set(cv2.CAP_PROP_POS_FRAMES,int(t*fps));ok,frame=cap.read()
   if not ok:continue
   im=frame[:,int(.34*w):int(.75*w)].copy()
   for y in [int(.4*h),int(.6*h)]:cv2.line(im,(0,y),(im.shape[1]-1,y),(0,220,255),3)
   image=Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB));x=i%4*400;y=i//4*560;sheet.paste(ImageOps.contain(image,(395,530)),(x,y));d.text((x+3,y+532),f't={t}s',fill='black')
  sheet.save(OUT/f'{name}_{page+1}.jpg',quality=94)
cap.release();print(json.dumps({'job':os.environ['SLURM_JOB_ID'],'source_only':True}),flush=True)
