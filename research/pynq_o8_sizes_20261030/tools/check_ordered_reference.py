from pathlib import Path
from datetime import datetime,timezone
import os,sys,socket,json,hashlib
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(4)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
protocol=json.loads((ROOT/'protocol/ordered_float_reference_v2.json').read_text())
for key,name in [('new_ordered_reference_sha256','ordered_float_reference.py'),('ordered_hybrid_executor_sha256','ordered_hybrid_executor.py')]:assert sha(ROOT/'tools'/name)==protocol[key]
D=ROOT/'s320/compiler_workspace';sys.path[:0]=[str(ROOT/'tools'),str(D/'pc_intdw')]
from ordered_hybrid_executor import YOLOHybridExecutor
from ordered_float_reference import contract_toys
from integer_backend import TorchIntegerBackend
out=ROOT/'results/ordered_reference';out.mkdir(parents=True,exist_ok=False);toys=contract_toys();rows=[]
for size in [192,256,320]:
 q=PROJECT/'pynq_rot192_compile_20261029/results/qualification' if size==192 else ROOT/('s'+str(size))/'results/qualification'
 reference=YOLOHybridExecutor(q/'compiled/model',TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)
 for i in range(8):
  with np.load(q/('parity_train_'+str(i)+'.npz')) as a:x=a['input'];native=a['native_integer_raw'];original=a['reference_integer_raw']
  ordered=reference.run(x).copy()
  box=float(np.max(np.abs(ordered[:,:,:4]-native[:,:,:4])));score=float(np.max(np.abs(ordered[:,:,4]-native[:,:,4])))
  file=out/('size'+str(size)+'_vector'+str(i)+'.npz');np.savez_compressed(file,ordered_reference=ordered,prior_native=native,original_numpy_reference=original)
  rows.append({'size':size,'index':i,'ordered_full_raw_bytes_exact_to_prior_native':ordered.tobytes()==native.tobytes(),
   'original_numpy_full_raw_bytes_exact_to_prior_native':original.tobytes()==native.tobytes(),
   'maximum_box_error':box,'maximum_score_error':score,'classes_exact':bool(np.array_equal(ordered[:,:,5],native[:,:,5])),
   'passes_original_value_thresholds':box<=.002 and score<=.0001 and np.array_equal(ordered[:,:,5],native[:,:,5]),
   'file':file.relative_to(ROOT).as_posix(),'sha256':sha(file)})
 result=[r for r in rows if r['size']==size];print(json.dumps({'size':size,'byte_exact_vectors':sum(r['ordered_full_raw_bytes_exact_to_prior_native'] for r in result)}),flush=True)
result={'status':'ALL24_FIXED_TRAIN_VECTORS_EXPLICIT_ORDERED_NONCONV_REFERENCE_CHECK_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
 'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/ordered_float_reference_v2.json'),'contract_toys':toys,'rows':rows,
 'actual_new_network_forwards':24,'original_numpy_reference_failures_not_rewritten':True,'native_engine_or_weights_changed':False,
 'all24_ordered_raw_bytes_exact':all(r['ordered_full_raw_bytes_exact_to_prior_native'] for r in rows),'whole_goal_complete':False}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
if not all(r['passes_original_value_thresholds'] for r in rows):raise SystemExit(2)
