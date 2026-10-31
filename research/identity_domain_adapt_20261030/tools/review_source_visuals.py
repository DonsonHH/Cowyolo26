from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];manifest=json.loads((ROOT/'results/source_visual_manifest.json').read_text());count=0
for sheet in manifest['files']:
 path=Path(sheet['file']);assert hashlib.sha256(path.read_bytes()).hexdigest()==sheet['sha256']
 with Image.open(path)as image:rendered=image.convert('RGB')
 for panel in sheet['panels']:
  source=Path(panel['source_file']);assert hashlib.sha256(source.read_bytes()).hexdigest()==panel['source_sha256']
  with Image.open(source)as image:expected=image.convert('RGB')
  expected.thumbnail((480,465),Image.Resampling.BILINEAR);x,y,w,h=panel['rect'];assert expected.size==(w,h)and expected.tobytes()==rendered.crop((x,y,x+w,y+h)).tobytes();count+=1
assert count==12
result={'status':'TWELVE_FIXED_NEW_TRAIN_ID_SOURCE_PANELS_PIXEL_BOUND_AND_ACTUALLY_VIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
        'panels':12,'actually_viewed':True,'files':[{'file':row['file'],'sha256':row['sha256'],'actually_viewed':True}for row in manifest['files']],
        'visual_findings':'Selected new training torso crops include blur and rotation padding. First/last selected files need not be the earliest/latest date because source selection was date round-robin. No reassignments, quality exclusions or future-ID pixels opened.',
        'new_model_forwards':0,'whole_goal_complete':False}
p=ROOT/'results/source_visual_review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'panels':12}))
