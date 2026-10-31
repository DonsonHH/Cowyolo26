"""Only new model/input queries run; verified galleries and query features reused."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,socket
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np
from PIL import Image
from frozen_body_tensor import body_tensor

ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
p=load(ROOT/'protocol/reference_v1.json')
for row in p['files']:assert sha(ROOT/row['file'])==row['sha256']
for name,digest in p['code_sha256'].items():assert sha(ROOT/name)==digest
out=ROOT/'results/reference';out.mkdir(parents=True,exist_ok=False)
with np.load(ROOT/'reference_input/prior_all_features.npz')as a:prior={key:a[key].copy()for key in a.files}
with np.load(ROOT/'reference_input/actual_galleries.npz')as a:actual_galleries={key:a[key].copy()for key in a.files}
arrays={};checks=[];gallery_checks=[];retrieval=[];total=0;reused=0
torch=None
if p['expected_new_Torch_image_forwards']:
 import torch
 from torchvision.models import mobilenet_v3_small
 torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(26);torch.use_deterministic_algorithms(True)
for model in p['models']:
 name=model['name'];assert sha(Path(model['checkpoint']))==model['checkpoint_sha256']
 gallery=prior[name+'_gallery_normalized'];gallery_raw=prior[name+'_gallery_raw']
 arrays[name+'_gallery_raw']=gallery_raw;arrays[name+'_gallery_normalized']=gallery
 assert gallery.shape==gallery_raw.shape==actual_galleries[name].shape==(30,576)
 for i in range(30):
  delta=float(np.max(np.abs(gallery[i]-actual_galleries[name][i])))
  dot=1-float(gallery[i].astype(float)@actual_galleries[name][i].astype(float))
  gallery_checks.append({'model':name,'index':i,'maximum_normalized_difference':delta,'one_minus_dot':dot,
                         'numeric_pass':delta<=1e-4 and dot<=1e-5,'new_forward':False})
 rows=[row for row in p['queries']if row['model']==name];encoder=full=None
 if any(row['cached_reference']is None for row in rows):
  full=mobilenet_v3_small(weights=None)
  encoder=torch.nn.Sequential(full.features,full.avgpool,torch.nn.Flatten()).eval()
  encoder.load_state_dict(torch.load(model['checkpoint'],map_location='cpu',weights_only=True))
  for par in encoder.parameters():par.requires_grad_(False)
 raws=[];features=[]
 for row in rows:
  with np.load(ROOT/row['vector_file'])as a:
   original_input=a['input'].copy();actual=a['normalized'].copy();actual_scores=a['scores'].copy()
  with Image.open(ROOT/row['photo_file'])as image:x=body_tensor(image)
  assert x.tobytes()==original_input.tobytes()and hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256']
  cached=row['cached_reference']
  if cached is None:
   with torch.inference_mode():raw=encoder(torch.from_numpy(x)).numpy().reshape(576).copy()
   total+=1;feature=raw/np.linalg.norm(raw);origin='new_Torch_query_forward'
  else:
   raw=prior[cached['raw_array']][cached['position']].copy();feature=prior[cached['normalized_array']][cached['position']].copy()
   reused+=1;origin='reused_verified_same_checkpoint_and_input'
  delta=float(np.max(np.abs(feature-actual)));dot=1-float(feature.astype(float)@actual.astype(float))
  raws.append(raw);features.append(feature)
  checks.append({'model':name,'query_index':row['query_index'],'input_tensor_sha256':row['input_tensor_sha256'],
                  'maximum_normalized_difference':delta,'one_minus_dot':dot,'input_byte_exact':True,
                  'numeric_pass':delta<=1e-4 and dot<=1e-5,'reference_origin':origin})
  for kind,g in[('same_actual_ARM_gallery',actual_galleries[name]),('reused_verified_Torch_gallery',gallery)]:
   scores=np.array([max(float(np.dot(feature.astype(float),g[j].astype(float)))for j,item in enumerate(p['gallery_images'])if item['identity']==identity)for identity in p['registered_IDs']])
   winner=int(np.argmax(scores))
   for policy,tau in p['thresholds'].items():
    accepted=bool(scores[winner]>=tau);expected=bool(actual_scores[int(np.argmax(actual_scores))]>=tau)
    retrieval.append({'model':name,'query_index':row['query_index'],'gallery':kind,'policy':policy,
      'predicted_id':p['registered_IDs'][winner],'accepted':accepted,
      'same_as_actual_ARM':p['registered_IDs'][winner]==row['predicted_id']and accepted==expected,
      'maximum_ID_score_difference':float(np.max(np.abs(scores-actual_scores))),'all_scores':scores.tolist()})
 arrays[name+'_query_raw']=np.stack(raws);arrays[name+'_query_normalized']=np.stack(features)
 del encoder,full
assert total==p['expected_new_Torch_image_forwards']and reused==p['expected_reused_query_features']
assert len(checks)==p['unique_model_input_queries']and len(gallery_checks)==60
numeric_failures=sum(not row['numeric_pass']for row in checks+gallery_checks)
decision_failures=sum(not row['same_as_actual_ARM']for row in retrieval)
np.savez_compressed(out/'all_features.npz',**arrays)
def save(path,value):
 with path.open('x')as f:json.dump(value,f,indent=2);f.write('\n')
for name,value in[('query_checks.json',checks),('gallery_checks.json',gallery_checks),('retrieval_checks.json',retrieval)]:save(out/name,value)
summary={'status':'REFERENCE_COMPLETE_ALL_NUMERICS_AND_FIXED_DECISIONS_MATCH'if not(numeric_failures or decision_failures)else'REFERENCE_COMPLETE_WITH_NUMERIC_OR_DECISION_DIFFERENCES',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),
 'actual_Torch_image_forwards':total,'new_gallery_image_forwards':0,'reused_gallery_vectors':60,
 'reused_unique_query_features':reused,'unique_model_input_queries':len(checks),
 'actual_query_jobs_represented':p['actual_job_count'],'network_calls':total,'warmups':0,
 'numeric_failures':numeric_failures,'retrieval_comparisons':len(retrieval),'retrieval_failures':decision_failures,
 'maximum_query_normalized_error':max(row['maximum_normalized_difference']for row in checks),
 'maximum_gallery_normalized_error':max(row['maximum_normalized_difference']for row in gallery_checks),
 'new_board_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
