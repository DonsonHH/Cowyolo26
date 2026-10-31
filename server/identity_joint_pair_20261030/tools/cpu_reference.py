from pathlib import Path
from datetime import datetime,timezone
import os,socket,hashlib,json,traceback
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import numpy as np
import torch,ncnn
from torchvision.models import mobilenet_v3_small

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')

assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
torch.set_num_threads(4);torch.set_num_interop_threads(1)
plan=load(ROOT/'protocol/cpu_reference_v1.json');execution=load(ROOT/'protocol/cpu_execution_v1.json')
assert sha(ROOT/'protocol/cpu_reference_v1.json')==execution['protocol_sha256']
for file,digest in execution['code_sha256'].items():assert sha(ROOT/file)==digest
for name in['checkpoint','NCNN_param','NCNN_bin']:assert sha(plan[name])==plan[name+'_sha256']
assert sha(ROOT/'input40.npz')==plan['input_archive_sha256']
out=ROOT/'results/cpu_reference';out.mkdir(parents=True,exist_ok=False)
state={'status':'RUNNING','created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),'Torch_image_forwards':0,'NCNN_image_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
try:
 full=mobilenet_v3_small(weights=None);encoder=torch.nn.Sequential(full.features,full.avgpool,torch.nn.Flatten()).eval()
 encoder.load_state_dict(torch.load(plan['checkpoint'],map_location='cpu',weights_only=True))
 net=ncnn.Net();net.opt.num_threads=1;net.opt.use_fp16_storage=False;net.opt.use_fp16_packed=False;net.opt.use_fp16_arithmetic=False;net.opt.use_bf16_storage=False
 assert net.load_param(plan['NCNN_param'])==0 and net.load_model(plan['NCNN_bin'])==0
 with np.load(ROOT/'input40.npz')as archive:inputs=archive['input'].copy()
 assert inputs.shape==(40,1,3,224,224)
 arrays={key:[]for key in['Torch_raw','Torch_normalized','NCNN_raw','NCNN_normalized']};records=[]
 for row,x in zip(plan['images'],inputs):
  assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256']
  with torch.inference_mode():a=encoder(torch.from_numpy(x)).numpy().reshape(576).copy()
  state['Torch_image_forwards']+=1;extractor=net.create_extractor();assert extractor.input('in0',ncnn.Mat(x[0]))==0
  rc,value=extractor.extract('out0');assert rc==0;b=np.asarray(value).reshape(576).copy();state['NCNN_image_forwards']+=1
  assert np.isfinite(a).all()and np.isfinite(b).all();an=a/np.linalg.norm(a);bn=b/np.linalg.norm(b);error=float(np.max(np.abs(an-bn)));distance=1-float(an.astype(float)@bn.astype(float))
  assert error<=1e-4 and distance<=1e-5
  for key,v in[('Torch_raw',a),('Torch_normalized',an),('NCNN_raw',b),('NCNN_normalized',bn)]:arrays[key].append(v)
  records.append({'index':row['index'],'input_tensor_sha256':row['input_tensor_sha256'],'maximum_normalized_error':error,'one_minus_dot':distance})
 np.savez_compressed(out/'all_features.npz',**{key:np.stack(value)for key,value in arrays.items()});save(out/'input_and_numeric_rows.json',records)
 state.update({'status':'ALL40_FIXED_AUG19_GALLERY_AND_ACTUAL_PHOTO_TORCH_NCNN_REFERENCE_PASS','maximum_normalized_error':max(row['maximum_normalized_error']for row in records)})
except BaseException as error:state.update({'status':'FAILED','error':repr(error),'traceback':traceback.format_exc()});raise
finally:save(out/'summary.json',state);print(json.dumps(state),flush=True)
