"""Diagnostic only: intervene at the first divergent attention INT8 boundary."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,sys,socket,hashlib
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np,torch
ROOT=Path(__file__).resolve().parents[1];CASE=ROOT/'s320';D=CASE/'compiler_workspace';Q=CASE/'results/qualification'
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(4)
sys.path[:0]=[str(D),str(D/'pc_intdw')]
from native_graph import NativeGraph
from hybrid_executor import YOLOHybridExecutor
from integer_backend import TorchIntegerBackend
out=ROOT/'results/probe320_causal';out.mkdir(parents=True,exist_ok=False)
with np.load(Q/'parity_train_4.npz') as a:x=a['input'];oldref=a['reference_integer_raw'];oldnative=a['native_integer_raw']
meta=json.loads((Q/'compiled/program/program.json').read_text());producer={v:n for n in meta['nodes'] for v in n['outputs']};live=set();stack=[meta['names'][meta['output_id']]]
while stack:
 name=stack.pop()
 if name in live:continue
 live.add(name)
 if name in producer:stack.extend(producer[name]['inputs'])
graph=NativeGraph(320,pc=True,library='native_queue_linux.so',program=str(Q/'compiled/program'),model_dir=str(Q/'compiled/model'),
 plan=str(Q/'resident_plan_all/resident_plan.bin'),options=4,debug_mirror=True)
actual=graph.run(x).copy();assert actual.tobytes()==oldnative.tobytes()
target='/model.10/m/m.0/attn/Add_output_0_QuantizeLinear_Output';source='/model.10/m/m.0/attn/Add_output_0'
native_q=graph.tensor(target).copy();native_f=graph.tensor(source).copy()
ref=YOLOHybridExecutor(Q/'compiled/model',TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)
reference_q=reference_f=None
def capture(name,value,node):
 global reference_q,reference_f
 if name==target:reference_q=value.copy()
 if name==source:reference_f=value.copy()
baseline=ref.run(x,boundary_callback=capture);assert baseline.tobytes()==oldref.tobytes()
indices=np.flatnonzero(reference_q.reshape(-1)!=native_q.reshape(-1));assert indices.tolist()==[7528]
qnode=producer[target];scale=ref.constants[qnode['inputs'][1]];zero=ref.constants[qnode['inputs'][2]]
boundary={'tensor':target,'flat_index':7528,'reference_int8':int(reference_q.reshape(-1)[7528]),'native_int8':int(native_q.reshape(-1)[7528]),
 'reference_float':float(reference_f.reshape(-1)[7528]),'native_float':float(native_f.reshape(-1)[7528]),
 'scale':float(scale),'zero':int(zero),'reference_float_over_scale':float(reference_f.reshape(-1)[7528]/scale),
 'native_float_over_scale':float(native_f.reshape(-1)[7528]/scale)}
def intervention(name,value,node):
 if name==target:value[...] = native_q
patched=ref.run(x,boundary_callback=intervention)
np.savez_compressed(out/'causal_arrays.npz',input=x,original_reference=baseline,native=actual,reference_with_one_native_INT8_boundary=patched,
 reference_boundary_float=reference_f,native_boundary_float=native_f,reference_boundary_INT8=reference_q,native_boundary_INT8=native_q)
graph.close()
result={'status':'FIRST_ATTENTION_INT8_BOUNDARY_INTERVENTION_EXECUTED_DIAGNOSTIC_ONLY','created_UTC':datetime.now(timezone.utc).isoformat(),
 'job_id':os.environ['SLURM_JOB_ID'],'boundary':boundary,'full_reference_matches_native_after_one_boundary_intervention':patched.tobytes()==actual.tobytes(),
 'original_reference_vs_native_complete_raw_gate_passes':False,'original_gates_or_weights_changed':False,
 'conf02_kept_output_rows_were_exact_before_intervention':oldref[oldref[:,:,4]>=.2].tobytes()==actual[actual[:,:,4]>=.2].tobytes(),
 'actual_network_forwards':3,'intervention_is_not_deployment_fix':True,'whole_goal_complete':False}
(out/'summary.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
