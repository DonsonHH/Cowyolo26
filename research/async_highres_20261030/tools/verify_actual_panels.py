from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=load(ROOT/'results/actual_photo_manifest.json');count=0
for page in manifest['files']:
 assert sha(page['file'])==page['sha256']
 with Image.open(page['file']) as im:im.load();canvas=im.convert('RGB')
 for panel in page['panels']:
  assert sha(panel['photo_file'])==panel['photo_sha256']
  with Image.open(panel['photo_file']) as im:im.load();thumb=im.convert('RGB');thumb.thumbnail((280,160),Image.Resampling.BILINEAR)
  x,y,w,h=panel['rect'];assert thumb.size==(w,h) and canvas.crop((x,y,x+w,y+h)).tobytes()==thumb.tobytes();count+=1
assert count==manifest['actual_photos']
result={'status':'ALL_ACTUAL_PHOTO_CONTACT_THUMBNAILS_MATCH_FULL_NATIVE_PHOTOS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'panels':count,'files':[{'file':r['file'],'sha256':r['sha256']} for r in manifest['files']],
 'actually_viewed':False,'scope':'Pixel binding only; assistant visual review recorded separately after viewing all panels.'}
f=ROOT/'results/actual_panel_pixel_verification.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'panels':count,'sheets':len(manifest['files'])}))
