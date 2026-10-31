"""Re-encode the same gallery with the new encoder before timed paired runs."""
from pathlib import Path
import hashlib,json,time,sys
import numpy as np
from PIL import Image
LEGACY=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
sys.path.insert(0,str(LEGACY))
from ncnn_encoder_v3 import Encoder,body_tensor

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')

def qualify(root,plan):
 root=Path(root);out=root/'results/identity_qualification';out.mkdir(exist_ok=False)
 state={'status':'RUNNING','measured_forwards':0,'warmup_forwards':0,'rows':[]};encoder=None
 try:
  with np.load(root/'reference40.npz')as a:reference={key:a[key].copy()for key in a.files}
  images=plan['identity_reference_images'];inputs=[]
  for row in images:
   assert sha(row['board_image'])==row['image_sha256']
   with Image.open(row['board_image'])as image:x=body_tensor(image)
   assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256'];inputs.append(x)
  save(out/'input_gate.json',{'status':'ALL40_ORIGINAL_BOARD_IMAGES_AND_INPUT_HASHES_EXACT_BEFORE_MODEL_CREATION','model_forwards':0})
  encoder=Encoder(Path(plan['models']['new']['encoder_directory']),threads=1);encoder.run(inputs[0]);state['warmup_forwards']+=1
  raws=[];features=[]
  for row,x in zip(images,inputs):
   start=time.monotonic_ns();raw=encoder.run(x);state['measured_forwards']+=1;ms=(time.monotonic_ns()-start)/1e6
   f=raw/np.linalg.norm(raw);index=row['index'];error=float(np.max(np.abs(f-reference['Torch_normalized'][index])));other=float(np.max(np.abs(f-reference['NCNN_normalized'][index])));d=1-float(f.astype(float)@reference['Torch_normalized'][index].astype(float))
   assert error<=1e-4 and other<=1e-4 and d<=1e-5
   raws.append(raw);features.append(f);state['rows'].append({'index':index,'input_tensor_sha256':row['input_tensor_sha256'],'raw_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),'normalized_Torch_error':error,'normalized_NCNN_error':other,'one_minus_dot':d,'network_ms':ms})
  raws=np.stack(raws);features=np.stack(features);np.savez_compressed(out/'all_features.npz',raw=raws,normalized=features)
  gallery=features[:30].astype(float);labels=plan['registered_IDs'];grows=images[:30];expected=[]
  for i,row in enumerate(images[30:]):
   dots=features[30+i].astype(float)@gallery.T;scores=np.array([max(dots[j]for j,r in enumerate(grows)if r['identity']==label)for label in labels]);winner=int(np.argmax(scores))
   expected.append({'fixed_job_index':i,'raw_feature_sha256':hashlib.sha256(raws[30+i].tobytes()).hexdigest(),'predicted_id':labels[winner],'similarity':float(scores[winner]),'accepted':bool(scores[winner]>=plan['fixed_identity_threshold']),'scores':[float(v)for v in scores]})
  save(out/'expected_queries.json',expected);state.update({'status':'NEW_ENCODER40_GALLERY_AND_FIXED_PHOTO_QUALIFICATION_PASS','gallery_images':30,'query_images':10})
  return state
 finally:
  if encoder:encoder.close()
  save(out/'record.json',state)
