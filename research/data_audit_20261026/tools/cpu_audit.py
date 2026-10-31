from pathlib import Path
import os,json,hashlib,zipfile,time,cv2,numpy as np
from PIL import Image,ImageOps,ImageDraw
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026');OUT=ROOT/'results'/os.environ.get('AUDIT_RUN_NAME','cpu_audit');OUT.mkdir(parents=True,exist_ok=True)
report={'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'hostname':os.uname().nodename,'videos':[]}
archive=ROOT/'data/opencows2020/OpenCows2020.local-copy.zip.partial'
if archive.exists() and archive.stat().st_size==2272138852:
 sha=hashlib.sha256()
 with archive.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):sha.update(b)
 digest=sha.hexdigest();report['opencows_archive_sha256']=digest
 if digest!='53c437eb2e383092967d218655afac74a20403850ab9dde1d136a570d948362c':raise ValueError('archive hash mismatch')
 with zipfile.ZipFile(archive) as z:
  prefix='10m32xl88x2b61zlkkgz3fml17/'
  dest=ROOT/'data/opencows2020/extracted'
  for n in z.namelist():
   if n.endswith('/') or n.endswith(('.html','.rdf')) or '/.' in n:continue
   relative=Path(n.removeprefix(prefix))
   if relative.is_absolute() or '..' in relative.parts:raise ValueError('unsafe member')
   p=dest/relative;p.parent.mkdir(parents=True,exist_ok=True)
   if not p.exists():p.write_bytes(z.read(n))
 report['opencows_extracted']=True
 # Rename only after the local-copy transfer is complete and verified.
 target=archive.with_name('OpenCows2020.zip')
 if not target.exists():archive.rename(target)
paths=sorted([p for p in (ROOT/'data').rglob('*') if p.suffix.lower() in ('.avi','.mp4')])
for p in paths:
 cap=cv2.VideoCapture(str(p));n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=float(cap.get(cv2.CAP_PROP_FPS));w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH));h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
 sha=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):sha.update(b)
 row={'path':str(p),'bytes':p.stat().st_size,'sha256':sha.hexdigest(),'open':cap.isOpened(),'width':w,'height':h,'fps':fps,'frames_reported':n,'duration_s':n/fps if fps else None};tiles=[]
 for fraction in (0,.1,.25,.5,.75,.9):
  cap.set(cv2.CAP_PROP_POS_FRAMES,max(0,int(n*fraction)));ok,frame=cap.read()
  if ok:tiles.append((fraction,Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))))
 cap.release();row['seek_decode_samples']=len(tiles)
 cap=cv2.VideoCapture(str(p));decoded=0
 while True:
  ok,_=cap.read()
  if not ok:break
  decoded+=1
 cap.release();row['fully_decoded_frames']=decoded;row['decode_count_matches_header']=decoded==n
 if tiles:
  sheet=Image.new('RGB',(3*480,2*310),'white');d=ImageDraw.Draw(sheet)
  for i,(frac,im) in enumerate(tiles):
   sheet.paste(ImageOps.contain(im,(475,280)),((i%3)*480,(i//3)*310));d.text(((i%3)*480+3,(i//3)*310+283),f'{frac:.2f} of video',fill='black')
  name=p.parent.name+'_'+p.stem
  if 'multicam_samples' in p.parts:name=p.parent.name+'_'+p.stem
  sheet.save(OUT/(name+'.jpg'),quality=88);row['contact_sheet']=name+'.jpg'
 report['videos'].append(row)
 print(json.dumps(row),flush=True)
(OUT/'media_audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({'slurm_job':report['slurm_job_id'],'video_count':len(paths),'opencows_extracted':report.get('opencows_extracted',False)}),flush=True)
