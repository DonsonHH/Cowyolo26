from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];manifest=json.loads((ROOT/'results/training_visual_manifest.json').read_text());panels=0
for sheet in manifest['files']:
 path=Path(sheet['file']);assert hashlib.sha256(path.read_bytes()).hexdigest()==sheet['sha256']
 with Image.open(path)as image:rendered=image.convert('RGB')
 with np.load(sheet['source_tensor_file'])as archive:inputs=archive['input'].copy()
 for row in sheet['panels']:
  value=inputs[row['input_index']];assert hashlib.sha256(value.tobytes()).hexdigest()==row['tensor_sha256']
  rgb=np.rint(np.clip((value*np.array([.229,.224,.225],np.float32)[:,None,None]+np.array([.485,.456,.406],np.float32)[:,None,None])*255,0,255)).astype(np.uint8).transpose(1,2,0).copy()
  assert hashlib.sha256(rgb.tobytes()).hexdigest()==row['display_RGB_sha256'];x,y,w,h=row['rect'];assert rendered.crop((x,y,x+w,y+h)).tobytes()==rgb.tobytes();panels+=1
assert panels==24 and len(manifest['files'])==6
result={'status':'ALL6_FIRST_ACTUAL_TRAINING_BATCHES24_TENSOR_PANELS_PIXEL_BOUND_AND_ACTUALLY_VIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
        'actual_training_panels':24,'actually_viewed':True,'files':[{'file':row['file'],'sha256':row['sha256'],'actually_viewed':True}for row in manifest['files']],
        'scope':'Only first4 of each condition first32 training inputs viewed. Inverse normalisation is a display conversion, original tensor bytes retained; not all57600 augmentations independently replayed.',
        'new_model_forwards':0,'whole_goal_complete':False}
p=ROOT/'results/training_visual_review.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'panels':24}))
