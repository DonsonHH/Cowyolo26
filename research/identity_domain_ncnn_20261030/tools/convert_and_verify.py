from pathlib import Path
from datetime import datetime,timezone
import os
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
import hashlib,json,socket,subprocess,time,traceback,sys
import numpy as np
from PIL import Image
import torch,ncnn
from torchvision.models import mobilenet_v3_small
from frozen_body_tensor import body_tensor

ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads(Path(path).read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):assert not path.exists();path.write_text(json.dumps(value,indent=2)+'\n')


assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
torch.set_num_threads(4);torch.set_num_interop_threads(1)
p=load(ROOT/'protocol/run_v1.json');e=load(ROOT/'protocol/execution_v1.json')
assert sha(ROOT/'protocol/run_v1.json')==e['protocol_sha256']
for name,digest in e['code_hashes'].items():assert sha(ROOT/'tools'/name)==digest
assert sha(p['checkpoint'])==p['checkpoint_sha256']and sha(p['converter'])==p['converter_sha256']
out=ROOT/'results/export';out.mkdir(parents=True,exist_ok=False)
state={'status':'RUNNING','created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),
       'actual_trace_Python_forward_calls':0,'measured_Torch_image_forwards':0,'measured_NCNN_image_forwards':0,
       'converter_internal_TorchScript_probe_count':'not_instrumented_unknown_additional','new_training_updates':0,'new_board_forwards':0,'whole_goal_complete':False}
try:
 full=mobilenet_v3_small(weights=None);encoder=torch.nn.Sequential(full.features,full.avgpool,torch.nn.Flatten()).eval()
 encoder.load_state_dict(torch.load(p['checkpoint'],map_location='cpu',weights_only=True))
 for parameter in encoder.parameters():parameter.requires_grad_(False)
 with Image.open(p['images'][0]['image_path'])as image:probe=torch.from_numpy(body_tensor(image))
 def trace_hook(module,args):state['actual_trace_Python_forward_calls']+=1
 handle=encoder.register_forward_pre_hook(trace_hook)
 traced=torch.jit.trace(encoder,(probe,),check_trace=False,strict=True);handle.remove();traced.save(str(out/'encoder.pt'))
 command=[p['converter'],'encoder.pt','inputshape=[1,3,224,224]','fp16=0','device=cpu']
 completed=subprocess.run(command,cwd=out,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (out/'converter.stdout.log').write_bytes(completed.stdout);(out/'converter.stderr.log').write_bytes(completed.stderr)
 save(out/'converter_command.json',{'argv':command,'returncode':completed.returncode,'converter_sha256':p['converter_sha256'],
                                   'NCNN_Python_generated_wrapper_executed':False,'internal_probe_count_known':False})
 assert completed.returncode==0
 for name in['encoder.ncnn.param','encoder.ncnn.bin']:assert(out/name).is_file()and(out/name).stat().st_size>0
 net=ncnn.Net();net.opt.num_threads=1
 net.opt.use_fp16_storage=False;net.opt.use_fp16_packed=False;net.opt.use_fp16_arithmetic=False;net.opt.use_bf16_storage=False
 assert net.load_param(str(out/'encoder.ncnn.param'))==0 and net.load_model(str(out/'encoder.ncnn.bin'))==0
 prior={}
 for group,path in p['reference_files'].items():
  assert sha(path)==p['reference_sha256'][group]
  with np.load(path)as archive:prior[group]=archive['normalized'].copy()
 arrays={key:[]for key in['Torch_raw','NCNN_raw','Torch_normalized','NCNN_normalized']};records=[];group_offsets={group:0 for group in p['groups']}
 anchors=out/'anchors';anchors.mkdir()
 for index,row in enumerate(p['images']):
  assert sha(row['image_path'])==row['image_SHA256']
  with Image.open(row['image_path'])as image:x=body_tensor(image)
  start=time.perf_counter_ns()
  with torch.inference_mode():reference=encoder(torch.from_numpy(x)).numpy().reshape(576).copy()
  torch_ms=(time.perf_counter_ns()-start)/1e6;state['measured_Torch_image_forwards']+=1
  start=time.perf_counter_ns();extractor=net.create_extractor();assert extractor.input('in0',ncnn.Mat(x[0]))==0
  code,value=extractor.extract('out0');assert code==0
  actual=np.asarray(value).reshape(576).copy();native_ms=(time.perf_counter_ns()-start)/1e6;state['measured_NCNN_image_forwards']+=1
  assert np.isfinite(reference).all()and np.isfinite(actual).all();a=reference/np.linalg.norm(reference);b=actual/np.linalg.norm(actual)
  error=float(np.max(np.abs(a-b)));cosine=1-float(a.astype(float)@b.astype(float))
  assert error<=p['max_normalized_NCNN_vs_Torch_error']and cosine<=p['max_1_minus_cosine_error']
  group=row['group'];position=group_offsets[group];group_offsets[group]+=1
  prior_error=float(np.max(np.abs(a-prior[group][position])));assert prior_error<=p['max_Torch_vs_prior_normalized_error']
  for key,array in[('Torch_raw',reference),('NCNN_raw',actual),('Torch_normalized',a),('NCNN_normalized',b)]:arrays[key].append(array)
  if index in p['anchor_indices']:np.savez_compressed(anchors/('index'+str(index)+'.npz'),input=x,Torch_raw=reference,NCNN_raw=actual)
  records.append({'index':index,'group':group,'source_index':row['source_index'],'input_tensor_sha256':hashlib.sha256(x.tobytes()).hexdigest(),
                  'Torch_ms':torch_ms,'server_NCNN_ms':native_ms,'max_normalized_NCNN_vs_Torch_error':error,'one_minus_cosine':cosine,'Torch_vs_prior_error':prior_error})
  if(index+1)%90==0:print(json.dumps({'images_verified':index+1,'Torch_forwards':state['measured_Torch_image_forwards'],'NCNN_forwards':state['measured_NCNN_image_forwards']}),flush=True)
 arrays={key:np.stack(value)for key,value in arrays.items()};np.savez_compressed(out/'all_features.npz',**arrays);save(out/'input_and_numeric_rows.json',records)
 parity=[];cal_changes=[];failures=[]
 gallery_IDs=p['eval_registered_IDs'];scopes=[('calibration',None),('fold0',gallery_IDs[:20]),('fold1',gallery_IDs[20:]),('full40',gallery_IDs),('retention',None)]
 for scope,IDs in scopes:
  group='calibration'if scope=='calibration'else'retention'if scope=='retention'else'evaluation'
  gi=[index for index,row in enumerate(p['images'])if row['group']==group and row['purpose']=='gallery'and(IDs is None or row['identity']in IDs)]
  qi=[index for index,row in enumerate(p['images'])if row['group']==group and row['purpose']!='gallery'and(IDs is None or not row['is_known']or row['identity']in IDs)]
  labels=sorted({p['images'][index]['identity']for index in gi});scores={}
  for backend in['Torch','NCNN']:
   values=arrays[backend+'_normalized'][qi].astype(float)@arrays[backend+'_normalized'][gi].astype(float).T
   scores[backend]=np.stack([values[:,[j for j,index in enumerate(gi)if p['images'][index]['identity']==label]].max(axis=1)for label in labels],axis=1)
  policies=[('Cows_calibrated',p['new_Cows_threshold']),('original_MultiCam',p['original_MultiCam_threshold'])]if scope!='retention'else[('original_MultiCam',p['original_MultiCam_threshold'])]
  for policy,tau in policies:
   for pos,index in enumerate(qi):
    first=int(np.argmax(scores['Torch'][pos]));second=int(np.argmax(scores['NCNN'][pos]));acceptA=bool(scores['Torch'][pos,first]>=tau);acceptB=bool(scores['NCNN'][pos,second]>=tau)
    row={'scope':scope,'policy':policy,'image_index':index,'Torch_Top1':labels[first],'NCNN_Top1':labels[second],
         'Torch_accepted':acceptA,'NCNN_accepted':acceptB,'same_Top1_and_accept':first==second and acceptA==acceptB,
         'maximum_registered_score_difference':float(np.max(np.abs(scores['Torch'][pos]-scores['NCNN'][pos])))}
    if scope=='calibration':cal_changes.append(row)
    else:
     parity.append(row)
     if not row['same_Top1_and_accept']:failures.append(row)
 save(out/'development_retrieval_parity.json',parity);save(out/'calibration_endpoint_differences.json',cal_changes)
 state.update({'measured_Torch_image_forwards':630,'measured_NCNN_image_forwards':630,'maximum_normalized_NCNN_vs_Torch_error':max(row['max_normalized_NCNN_vs_Torch_error']for row in records),
               'maximum_Torch_vs_prior_error':max(row['Torch_vs_prior_error']for row in records),'development_decisions_checked':len(parity),
               'development_decision_differences':len(failures),'calibration_endpoint_decision_differences':sum(not row['same_Top1_and_accept']for row in cal_changes),
               'NCNN_operators':sorted({line.split()[0]for line in(out/'encoder.ncnn.param').read_text().splitlines()[2:]if line.strip()}),
               'NCNN_param_sha256':sha(out/'encoder.ncnn.param'),'NCNN_bin_sha256':sha(out/'encoder.ncnn.bin')})
 assert len(parity)==1260 and not failures
 state['status']='NEW_DOMAIN_ENCODER_FP32_NCNN630_IMAGE_PARITY_AND1260_DEVELOPMENT_DECISIONS_PASS'
except BaseException as error:
 state.update({'status':'FAILED','error':repr(error),'traceback':traceback.format_exc()});raise
finally:
 save(out/'summary.json',state);print(json.dumps(state),flush=True)
