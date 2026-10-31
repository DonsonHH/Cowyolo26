"""Fresh CPU Torch reference on every actual photo and all30 gallery images."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,sys,os,socket,time,tarfile
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np,torch
from PIL import Image
from torchvision.models import mobilenet_v3_small
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
sys.path.insert(0,str(BASE/'pynq_identity_ncnn_20261029/input'))
from training_primitives import BodyTransform
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
torch.set_num_threads(4);torch.set_num_interop_threads(1)
p=load(ROOT/'protocol/reference_v1.json');e=load(ROOT/'protocol/reference_execution_v1.json')
assert sha(__file__)==e['script_sha256'] and sha(ROOT/'protocol/reference_v1.json')==e['protocol_sha256']
for row in p['input_files']:assert sha(ROOT/row['file'])==row['sha256']
checkpoint=Path(p['checkpoint']);assert sha(checkpoint)==p['checkpoint_sha256']
assert sha(BASE/'pynq_identity_ncnn_20261029/input/training_primitives.py')==p['training_primitives_sha256']
model=mobilenet_v3_small(weights=None);encoder=torch.nn.Sequential(model.features,model.avgpool,torch.nn.Flatten()).eval()
encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True));transform=BodyTransform()
for parameter in encoder.parameters():parameter.requires_grad_(False)
out=ROOT/'results/reference';out.mkdir(parents=True,exist_ok=False);rows=load(ROOT/'input/jobs.json')
labels=p['registered_IDs'];galleryrows=load(BASE/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery']
with np.load(ROOT/'input/board_gallery.npz') as ar:board_gallery=ar['new_gallery'].astype(float)
query_reference=[];query_actual=[];checks=[];time_rows=[]
for row in rows:
 with np.load(ROOT/row['vector_file']) as ar:
  with Image.open(ROOT/row['photo_file']) as image:x=transform(image).unsqueeze(0).contiguous()
  preprocessing_error=float(np.max(np.abs(x.numpy()-ar['input'])));assert preprocessing_error<=p['maximum_input_absolute_error']
  start=time.perf_counter_ns()
  with torch.inference_mode():raw=encoder(x).numpy().reshape(576).copy()
  elapsed=(time.perf_counter_ns()-start)/1e6
  normalized=raw/np.linalg.norm(raw);actual=ar['normalized'].copy();error=float(np.max(np.abs(normalized-actual)))
  cosine_error=1-float(normalized.astype(float)@actual.astype(float))
  assert error<=p['maximum_normalized_feature_absolute_error'] and cosine_error<=p['maximum_1_minus_cosine_error']
  query_reference.append(normalized);query_actual.append(actual);time_rows.append(elapsed)
  checks.append({'run':row['run'],'index':row['index'],'photo_file':row['photo_file'],'input_tensor_sha256':hashlib.sha256(x.numpy().tobytes()).hexdigest(),
   'maximum_input_absolute_error':preprocessing_error,'maximum_raw_feature_difference':float(np.max(np.abs(raw-ar['raw']))),
   'maximum_normalized_feature_difference':error,'one_minus_cosine':cosine_error,'Torch_CPU_ms':elapsed})
gallery_reference=[];gallery_checks=[]
for index,row in enumerate(galleryrows):
 assert sha(row['path'])==row['sha256']
 with Image.open(row['path']) as image:x=transform(image).unsqueeze(0).contiguous()
 with torch.inference_mode():raw=encoder(x).numpy().reshape(576).copy()
 normalized=raw/np.linalg.norm(raw);error=float(np.max(np.abs(normalized-board_gallery[index])));cosine_error=1-float(normalized.astype(float)@board_gallery[index])
 assert error<=p['maximum_normalized_feature_absolute_error'] and cosine_error<=p['maximum_1_minus_cosine_error']
 gallery_reference.append(normalized);gallery_checks.append({'index':index,'maximum_normalized_feature_difference':error,'one_minus_cosine':cosine_error})
ref=np.asarray(query_reference);actual=np.asarray(query_actual);refgallery=np.asarray(gallery_reference);retrieval=[]
for name,gallery in [('same_actual_board_gallery',board_gallery),('fresh_Torch_gallery',refgallery.astype(float))]:
 dot=ref.astype(float)@gallery.T
 scores=np.stack([np.max(dot[:,[i for i,r in enumerate(galleryrows) if r['identity']==label]],axis=1) for label in labels],axis=1)
 for index,(row,score) in enumerate(zip(rows,scores)):
  winner=int(np.argmax(score));accepted=bool(score[winner]>=p['fixed_threshold'])
  assert labels[winner]==row['predicted_id'] and accepted==row['accepted'],(name,index,labels[winner],row['predicted_id'],accepted,row['accepted'])
  retrieval.append({'gallery':name,'query_index':index,'predicted_id':labels[winner],'accepted':accepted,'maximum_score_difference':float(np.max(np.abs(score-np.asarray(row['actual_scores']))))})
np.savez_compressed(out/'all_reference_features.npz',query_Torch=ref,query_actual_ARM=actual,gallery_Torch=refgallery,gallery_actual_ARM=board_gallery)
save(out/'query_checks.json',checks);save(out/'gallery_checks.json',gallery_checks);save(out/'retrieval_checks.json',retrieval)
summary={'status':'ALL_ACTUAL_PHOTOS_AND30_GALLERY_TORCH_REFERENCE_PASS_FROZEN_NUMERIC_AND_RETRIEVAL_GATES','created_UTC':datetime.now(timezone.utc).isoformat(),
 'job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),'query_Torch_forwards':len(rows),'gallery_Torch_forwards':len(galleryrows),
 'maximum_query_normalized_error':max(c['maximum_normalized_feature_difference'] for c in checks),
 'maximum_gallery_normalized_error':max(c['maximum_normalized_feature_difference'] for c in gallery_checks),
 'maximum_input_error':max(c['maximum_input_absolute_error'] for c in checks),'retrieval_conditions':len(retrieval),
 'all_top1_and_threshold_decisions_same':True,'permanent_ID_accuracy_verified':False,'new_training_updates':0,'new_board_forwards':0,'whole_goal_complete':False}
save(out/'summary.json',summary)
files=sorted(f for f in out.rglob('*') if f.is_file());files.extend([ROOT/'protocol/reference_v1.json',ROOT/'protocol/reference_execution_v1.json',Path(__file__)])
manifest=ROOT/'reference_manifest.json';save(manifest,[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files])
archive=ROOT/'reference_delivery_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
save(ROOT/'reference_transfer.json',{'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1})
print(json.dumps(summary),flush=True)
