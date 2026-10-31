from pathlib import Path
import os,json,cv2
from PIL import Image,ImageOps,ImageDraw
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'results/dense_review';OUT.mkdir(parents=True,exist_ok=True)
rows=[]
for p in sorted((ROOT/'data/cows2021_samples').glob('*/RGB.avi')):
 cap=cv2.VideoCapture(str(p));n=int(cap.get(7));fps=cap.get(5);w=int(cap.get(3));h=int(cap.get(4));tiles=[];idx=0
 while True:
  ok,im=cap.read()
  if not ok:break
  if idx%8==0:
   cv2.line(im,(int(w*.4),0),(int(w*.4),h),(0,220,255),2);cv2.line(im,(int(w*.6),0),(int(w*.6),h),(0,220,255),2)
   tiles.append((idx,Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB))))
  idx+=1
 cap.release();cols=4;rowsn=(len(tiles)+cols-1)//cols
 sheet=Image.new('RGB',(cols*400,rowsn*250),'white');d=ImageDraw.Draw(sheet)
 for i,(f,im) in enumerate(tiles):
  x=(i%cols)*400;y=(i//cols)*250;sheet.paste(ImageOps.contain(im,(395,222)),(x,y));d.text((x+4,y+224),f'frame {f} t={f/fps:.3f}s',fill='black')
 name=p.parent.name+'_dense.jpg';sheet.save(OUT/name,quality=92)
 rows.append({'source':str(p),'fully_decoded_frames':idx,'reported_frames':n,'fps':fps,'sheet':name,'sampling_interval_frames':8,'job_id':os.environ.get('SLURM_JOB_ID')})
(OUT/'review_manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8');print(json.dumps(rows),flush=True)
