from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,socket,time
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np,torch
from PIL import Image
from torchvision.models import mobilenet_v3_small
from frozen_body_tensor import body_tensor

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]))
assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.manual_seed(26);torch.use_deterministic_algorithms(True)
p=load(ROOT/'protocol/reference_v1.json');e=load(ROOT/'protocol/reference_execution_v1.json')
assert sha(ROOT/'protocol/reference_v1.json')==e['protocol_sha256']
for name,digest in e['code_sha256'].items():assert sha(ROOT/name)==digest
for row in p['files']:assert sha(ROOT/row['file'])==row['sha256']
out=ROOT/'results/reference';out.mkdir(parents=True,exist_ok=False);arrays={};queries=[];gallery_checks=[];retrieval=[];total=0
for model in p['models']:
 name=model['name'];assert sha(model['checkpoint'])==model['checkpoint_sha256']
 full=mobilenet_v3_small(weights=None);encoder=torch.nn.Sequential(full.features,full.avgpool,torch.nn.Flatten()).eval()
 encoder.load_state_dict(torch.load(model['checkpoint'],map_location='cpu',weights_only=True))
 for par in encoder.parameters():par.requires_grad_(False)
 with np.load(ROOT/'reference_input/actual_galleries.npz')as a:actual_gallery=a[name].copy()
 gallery_raw=[];gallery_features=[]
 for i,row in enumerate(p['gallery_images']):
  assert sha(row['server_image'])==row['sha256']
  with Image.open(row['server_image'])as im:x=body_tensor(im)
  assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256']
  with torch.inference_mode():raw=encoder(torch.from_numpy(x)).numpy().reshape(576).copy()
  total+=1;feature=raw/np.linalg.norm(raw);delta=float(np.max(np.abs(feature-actual_gallery[i])));dot=1-float(feature.astype(float)@actual_gallery[i].astype(float))
  gallery_checks.append({'model':name,'index':i,'maximum_normalized_difference':delta,'one_minus_dot':dot,'numeric_pass':delta<=1e-4 and dot<=1e-5});gallery_raw.append(raw);gallery_features.append(feature)
 gallery_raw=np.stack(gallery_raw);gallery_features=np.stack(gallery_features);arrays[name+'_gallery_raw']=gallery_raw;arrays[name+'_gallery_normalized']=gallery_features
 actual_rows=[r for r in p['queries']if r['model']==name];raws=[];features=[]
 for row in actual_rows:
  with np.load(ROOT/row['vector_file'])as a:actual_raw=a['raw'].copy();actual=a['normalized'].copy();original_input=a['input'].copy();actual_scores=a['scores'].copy()
  with Image.open(ROOT/row['photo_file'])as im:x=body_tensor(im)
  assert x.tobytes()==original_input.tobytes()and hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256']
  with torch.inference_mode():raw=encoder(torch.from_numpy(x)).numpy().reshape(576).copy()
  total+=1;feature=raw/np.linalg.norm(raw);delta=float(np.max(np.abs(feature-actual)));dot=1-float(feature.astype(float)@actual.astype(float));raws.append(raw);features.append(feature)
  queries.append({'model':name,'query_index':row['query_index'],'input_tensor_sha256':row['input_tensor_sha256'],'maximum_normalized_difference':delta,'one_minus_dot':dot,'input_byte_exact':True,'numeric_pass':delta<=1e-4 and dot<=1e-5})
  for label,gallery in[('same_actual_ARM_gallery',actual_gallery),('fresh_Torch_gallery',gallery_features)]:
   scores=np.array([max(float(np.dot(feature.astype(float),gallery[j].astype(float)))for j,r in enumerate(p['gallery_images'])if r['identity']==identity)for identity in p['registered_IDs']])
   winner=int(np.argmax(scores))
   for policy,tau in p['thresholds'].items():
    accepted=bool(scores[winner]>=tau);expected=bool(actual_scores[int(np.argmax(actual_scores))]>=tau)
    retrieval.append({'model':name,'query_index':row['query_index'],'gallery':label,'policy':policy,'predicted_id':p['registered_IDs'][winner],'accepted':accepted,'same_as_actual_ARM':p['registered_IDs'][winner]==row['predicted_id']and accepted==expected,'maximum_ID_score_difference':float(np.max(np.abs(scores-actual_scores))),'all_scores':scores.tolist()})
  if len(queries)%10==0:print(json.dumps({'unique_queries_completed':len(queries),'actual_Torch_image_forwards':total}),flush=True)
 arrays[name+'_query_raw']=np.stack(raws);arrays[name+'_query_normalized']=np.stack(features)
 del encoder,full
assert total==p['expected_Torch_image_forwards']and len(gallery_checks)==60 and len(queries)==p['unique_model_input_queries']
numeric_failures=sum(not r['numeric_pass']for r in gallery_checks+queries);decision_failures=sum(not r['same_as_actual_ARM']for r in retrieval)
np.savez_compressed(out/'all_features.npz',**arrays);save(out/'query_checks.json',queries);save(out/'gallery_checks.json',gallery_checks);save(out/'retrieval_checks.json',retrieval)
summary={'status':'ALL_UNIQUE_TRIGGER_PHOTOS_AND_BOTH30_GALLERIES_TORCH_REFERENCE_AND_FIXED_DECISIONS_PASS'if not(numeric_failures or decision_failures)else'ALL_REFERENCE_FEATURES_SAVED_WITH_NUMERIC_OR_RETRIEVAL_FAILURE',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),'actual_Torch_image_forwards':total,'query_image_forwards':len(queries),'gallery_image_forwards':60,'network_calls':total,'warmups':0,
 'maximum_query_normalized_error':max(r['maximum_normalized_difference']for r in queries),'maximum_gallery_normalized_error':max(r['maximum_normalized_difference']for r in gallery_checks),'numeric_failures':numeric_failures,'retrieval_comparisons':len(retrieval),'retrieval_failures':decision_failures,
 'unique_queries':len(queries),'all_actual_query_jobs_represented':p['actual_job_count'],'new_board_forwards':0,'new_training_updates':0,'whole_goal_complete':False};save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
if numeric_failures or decision_failures:raise SystemExit(1)
