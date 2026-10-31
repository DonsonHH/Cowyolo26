from pathlib import Path
import json,zlib,hashlib,cv2,os,csv
from PIL import Image,ImageOps,ImageDraw
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2');SRC=ROOT/'data/mendeley_counting/selected_compressed';OUT=ROOT/'data/mendeley_counting/extracted';OUT.mkdir(exist_ok=True)
manifest=json.loads((SRC/'members_manifest.json').read_text());files=[];media=[]
for r in manifest['members']:
 p=Path(r['compressed_path']);raw=p.read_bytes();d=zlib.decompress(raw,-15) if r['compression']==8 else raw
 if len(d)!=r['bytes'] or f'{zlib.crc32(d):08x}'!=r['crc32']:raise ValueError('ZIP member verification failed: '+r['name'])
 dest=(OUT/r['name']).resolve()
 if not dest.is_relative_to(OUT.resolve()):raise ValueError('unsafe path')
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(d)
 files.append({'source_member':r['name'],'path':str(dest),'bytes':len(d),'crc32':r['crc32'],'sha256':hashlib.sha256(d).hexdigest()})
result=ROOT/'results/mendeley_source';result.mkdir(parents=True,exist_ok=True)
for f in files:
 p=Path(f['path'])
 if p.suffix.lower()!='.mp4':continue
 c=cv2.VideoCapture(str(p));fps=c.get(5);n=int(c.get(7));w=int(c.get(3));h=int(c.get(4));tiles=[];decoded=0
 while True:
  ok,im=c.read()
  if not ok:break
  if decoded in {int(n*x) for x in [0,.1,.2,.3,.4,.5,.6,.7,.8,.9]}:tiles.append((decoded,Image.fromarray(cv2.cvtColor(im,cv2.COLOR_BGR2RGB))))
  decoded+=1
 c.release();sheet=Image.new('RGB',(5*360,2*250),'white');dr=ImageDraw.Draw(sheet)
 for i,(idx,im) in enumerate(tiles):
  x=i%5*360;y=i//5*250;sheet.paste(ImageOps.contain(im,(355,220)),(x,y));dr.text((x+3,y+223),f'f={idx} t={idx/fps:.2f}s',fill='black')
 fn=p.stem+'_source.jpg';sheet.save(result/fn,quality=92)
 media.append({'path':str(p),'fps':fps,'width':w,'height':h,'reported_frames':n,'decoded_frames':decoded,'duration_s':n/fps,'sheet':fn})
gt=OUT/'Ground Truth/gt.txt';lines=gt.read_text().splitlines();preview=lines[:6];rows=[[float(x) for x in line.split(',')] for line in lines if line.strip()]
report={'job_id':os.environ['SLURM_JOB_ID'],'source_doi':'10.17632/dk54zg67dd.1','archive_fully_downloaded':False,'verification':'selected ZIP member sizes and CRC32 verified; extracted SHA256 recorded; published full archive SHA256 not locally established','files':files,'videos':media,'gt':{'rows':len(rows),'columns':sorted(set(len(x) for x in rows)),'preview':preview,'frame_min':min(x[0] for x in rows),'frame_max':max(x[0] for x in rows),'track_ids':sorted(set(x[1] for x in rows))}}
(result/'audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
