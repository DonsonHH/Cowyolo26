from pathlib import Path
import json,hashlib,inspect
import numpy as np
import PIL
from PIL import Image,ImageOps
from ncnn_encoder_v2 import body_tensor
ROOT=Path(__file__).resolve().parent
rows=[];out=ROOT/'preprocessing_diagnostic';out.mkdir(exist_ok=False)
for row in json.loads((ROOT/'vector_manifest.json').read_text()):
 with np.load(ROOT/row['file']) as a:expected=a['input']
 with Image.open(ROOT/row['image_file']) as im:
  im.load();rgb=np.asarray(im.convert('RGB'));actual=body_tensor(im)
 error=float(np.max(np.abs(actual-expected)))
 if error>1e-6:
  np.savez_compressed(out/(row['name']+'.npz'),runtime_input=actual,expected_input=expected,native_decoded_RGB=rgb)
 rows.append({'name':row['name'],'preprocess_max_absolute_error':error,'image_size_WH':list(rgb.shape[1::-1]),
 'decoded_native_RGB_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),'tensor_difference_elements':int(np.count_nonzero(actual!=expected)),
 'above1e6_elements':int(np.count_nonzero(np.abs(actual-expected)>1e-6))})
result={'Pillow':PIL.__version__,'pad_source':inspect.getsource(ImageOps.pad),'contain_source':inspect.getsource(ImageOps.contain),
 'rows':rows,'nonmatching_images':sum(r['preprocess_max_absolute_error']>1e-6 for r in rows),'max_error':max(r['preprocess_max_absolute_error'] for r in rows),'new_model_forwards':0}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['rows','pad_source','contain_source']}))
print(json.dumps([r for r in rows if r['preprocess_max_absolute_error']>1e-6][:10]))
