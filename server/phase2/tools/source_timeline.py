from pathlib import Path
import cv2,json,os,hashlib
from PIL import Image,ImageOps,ImageDraw
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'phase2/results/source_timeline';OUT.mkdir(parents=True,exist_ok=True)
src=ROOT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4'
cap=cv2.VideoCapture(str(src));fps=cap.get(5);n=int(cap.get(7));w=int(cap.get(3));h=int(cap.get(4))
specs=[('coarse_full',list(range(0,int(n/fps),5))),('dense_active',list(range(330,451)))]
manifest=[]
for name,times in specs:
 for page in range((len(times)+29)//30):
  subset=times[page*30:page*30+30];sheet=Image.new('RGB',(6*220,5*330),'white');d=ImageDraw.Draw(sheet)
  for i,t in enumerate(subset):
   cap.set(cv2.CAP_PROP_POS_FRAMES,int(t*fps));ok,im=cap.read()
   if not ok:continue
   crop=im[:,int(w*.34):int(w*.75)].copy()
   for y in [int(h*.4),int(h*.6)]:cv2.line(crop,(0,y),(crop.shape[1]-1,y),(0,220,255),3)
   image=Image.fromarray(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB));x=i%6*220;y=i//6*330;sheet.paste(ImageOps.contain(image,(215,300)),(x,y));d.text((x+3,y+303),f't={t}s f={int(t*fps)}',fill='black')
  fn=f'{name}_{page+1}.jpg';sheet.save(OUT/fn,quality=92);manifest.append({'file':fn,'seconds':subset,'source_only':True})
cap.release();(OUT/'timeline_manifest.json').write_text(json.dumps({'job':os.environ['SLURM_JOB_ID'],'source':str(src),'source_sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1','pages':manifest},indent=2))
print(json.dumps({'job':os.environ['SLURM_JOB_ID'],'pages':len(manifest),'mode':'source only, no model overlay'}),flush=True)
