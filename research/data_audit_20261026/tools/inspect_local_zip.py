from pathlib import Path, PurePosixPath
from collections import Counter
import zipfile,json,random,io,hashlib
from PIL import Image, ImageOps, ImageDraw

SRC=Path(r'C:\Users\Donson\Downloads\10m32xl88x2b61zlkkgz3fml17.zip\10m32xl88x2b61zlkkgz3fml17.zip')
OUT=Path(__file__).resolve().parent.parent/'local_opencows';OUT.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(SRC) as z:
 rows=[{'name':x.filename,'bytes':x.file_size,'compressed':x.compress_size,'crc32':f'{x.CRC:08x}'} for x in z.infolist() if not x.is_dir()]
 (OUT/'zip_members.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
 groups=Counter();exts=Counter()
 for r in rows:
  parts=PurePosixPath(r['name']).parts;groups['/'.join(parts[:2])]+=1;exts[PurePosixPath(r['name']).suffix.lower()]+=1
 print(json.dumps({'archive':str(SRC),'bytes':SRC.stat().st_size,'members':len(rows),'total_uncompressed':sum(r['bytes'] for r in rows),'groups':dict(groups),'extensions':dict(exts)},indent=2),flush=True)
 for r in rows:
  n=r['name']
  if PurePosixPath(n).name.lower() in ('readme.txt','license','licence','license.txt'):
   t=z.read(n).decode('utf8',errors='replace');(OUT/(PurePosixPath(n).name+'.txt')).write_text(t,encoding='utf8');print(t[:5000],flush=True)
 print('NON_IMAGE_SAMPLES',json.dumps([r['name'] for r in rows if PurePosixPath(r['name']).suffix.lower() not in ('.jpg','.jpeg','.png')][:22]),flush=True)
 images=[r['name'] for r in rows if r['name'].lower().endswith(('.jpg','.jpeg','.png')) and '__MACOSX' not in r['name']]
 subsets={k:[n for n in images if k in n] for k in ('detection_and_localisation','identification')}
 chosen=[]
 rng=random.Random(26)
 for key,names in subsets.items():
  if names:chosen+=rng.sample(names,min(12,len(names)))
 if not chosen: chosen=rng.sample(images,min(24,len(images)))
 w,h=4*340,((len(chosen)+3)//4)*245
 canvas=Image.new('RGB',(w,h),'white');draw=ImageDraw.Draw(canvas);summary=[]
 for i,n in enumerate(chosen):
  data=z.read(n)
  with Image.open(io.BytesIO(data)) as im:
   im.load();summary.append({'name':n,'width':im.width,'height':im.height,'mode':im.mode,'sha256':hashlib.sha256(data).hexdigest()})
   tile=ImageOps.contain(im.convert('RGB'),(330,210));x=(i%4)*340;y=(i//4)*245;canvas.paste(tile,(x,y));draw.text((x+3,y+212),PurePosixPath(n).name[:44],fill='black')
 canvas.save(OUT/'contact_sheet.jpg',quality=90)
 (OUT/'sample_metadata.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
 print('SAMPLE_METADATA',json.dumps(summary[:5]),flush=True)
