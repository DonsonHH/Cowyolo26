"""One frozen failing image, complete integer reference, unfused/fused native controls."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,os,sys,socket
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import torch,numpy as np
ROOT=Path(__file__).resolve().parents[1];CASE=ROOT/'s320';D=CASE/'compiler_workspace';Q=CASE/'results/qualification'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(4)
out=ROOT/'results/probe320';out.mkdir(parents=True,exist_ok=False)
with np.load(Q/'parity_train_4.npz') as a:x=a['input'];oldref=a['reference_integer_raw'];oldnative=a['native_integer_raw']
assert oldref.tobytes()!=oldnative.tobytes()
sys.path[:0]=[str(D),str(D/'pc_intdw')]
from native_graph import NativeGraph
from hybrid_executor import YOLOHybridExecutor
from integer_backend import TorchIntegerBackend
reference=YOLOHybridExecutor(Q/'compiled/model',TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)
captured={};order=[]
def snapshot(name,value,node):
 captured[name]=np.ascontiguousarray(value).copy();order.append((name,node['op'],node['name']))
current=reference.run(x,boundary_callback=snapshot);assert current.tobytes()==oldref.tobytes()
controls=[];firsts=[]
for options in [0,4]:
 graph=NativeGraph(320,pc=True,library='native_queue_linux.so',program=str(Q/'compiled/program'),model_dir=str(Q/'compiled/model'),
  plan=str(Q/'resident_plan_all/resident_plan.bin'),options=options,debug_mirror=True)
 actual=graph.run(x).copy();np.save(out/('native_options'+str(options)+'.npy'),actual)
 if options==4:assert actual.tobytes()==oldnative.tobytes()
 differences=[];unsupported=[]
 for name,op,node_name in order:
  if name not in graph.meta['names']:continue
  try:observed=graph.tensor(name)
  except RuntimeError as e:unsupported.append({'name':name,'error':str(e)});continue
  expected=captured[name]
  if observed.shape!=expected.shape:unsupported.append({'name':name,'shape_native':list(observed.shape),'shape_ref':list(expected.shape)});continue
  if observed.tobytes()!=expected.tobytes():
   delta=np.abs(observed.astype(np.float64)-expected.astype(np.float64));indices=np.flatnonzero(observed.reshape(-1)!=expected.reshape(-1))
   report={'name':name,'op':op,'node':node_name,'shape':list(expected.shape),'dtype_reference':str(expected.dtype),'dtype_native':str(observed.dtype),
    'max_error':float(delta.max()),'numeric_different_elements':len(indices),
    'first_difference_flat_indices':indices[:12].astype(int).tolist(),
    'reference_first_values':expected.reshape(-1)[indices[:12]].astype(float).tolist(),
    'native_first_values':observed.reshape(-1)[indices[:12]].astype(float).tolist()}
   differences.append(report)
   if len(differences)<=5:np.savez_compressed(out/('options'+str(options)+'_boundary'+str(len(differences))+'.npz'),reference=expected,native=observed)
 graph.close()
 controls.append({'options':options,'complete_raw_exact_to_reference':actual.tobytes()==oldref.tobytes(),
  'maximum_coordinate_error':float(np.max(np.abs(actual[:,:,:4]-oldref[:,:,:4]))),'max_score_error':float(np.max(np.abs(actual[:,:,4]-oldref[:,:,4]))),
  'boundary_differences':differences,'unavailable_boundaries':unsupported,'raw_sha256':hashlib.sha256(actual.tobytes()).hexdigest()})
result={'status':'FAILED320_SINGLE_VECTOR_REAL_REFERENCE_AND_TWO_NATIVE_CONTROLS_EXECUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'job_id':os.environ['SLURM_JOB_ID'],'failing_input_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'reference_output_reproduced_exact':True,
 'actual_network_forwards':3,'controls':controls,'original_gate_relaxed':False,'board320_inference_started':False,'whole_goal_complete':False}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'controls':[{'options':c['options'],'complete_raw_exact':c['complete_raw_exact_to_reference'],
 'first_different_boundaries':c['boundary_differences'][:4]} for c in controls]}),flush=True)
if not controls[-1]['complete_raw_exact_to_reference']:raise SystemExit(2)
