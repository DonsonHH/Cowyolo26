from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,py_compile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
diagnostic=load(ROOT/'evidence/input_normalization_diagnostic.json')
assert len(diagnostic)==8 and all(r['multiply_exact'] and not r['divide_exact'] for r in diagnostic)
old=ROOT/'tools/evaluate_quality.py';text=old.read_text()
assert text.count("from board_runtime import preprocess,decode")==1
text=text.replace("from board_runtime import preprocess,decode","from board_runtime import decode\n from frozen_input import preprocess")
text=text.replace('protocol/eval_v1.json','protocol/eval_v2.json').replace('protocol/execution_v1.json','protocol/execution_v2.json')
text=text.replace("out=ROOT/'results/quality'","out=ROOT/'results/quality_v2'")
text=text.replace("size=p['size'];out=",'''# All eight frozen CUDA tensors must be reproduced before any new forward.
 for key,digest in p['expected_NN_input_hashes'].items():
  with np.load(PROJECT/'factorial_lane_crop_20261029/results/roi/pixel_controls'/(key+'_NN.npz')) as archive:expected=archive['actual_input']
  pixels=np.rint(expected.transpose(1,2,0)*255).astype(np.uint8)[:,:,::-1].copy()
  observed=preprocess(pixels,p['size'])
  assert observed[0].tobytes()==expected.tobytes() and hashlib.sha256(observed.tobytes()).hexdigest()==digest
 size=p['size'];out=''')
file=ROOT/'tools/evaluate_quality_v2.py';assert not file.exists();file.write_text(text,newline='\n');py_compile.compile(str(file),doraise=True)
p=load(ROOT/'protocol/eval_v1.json');p.update({'status':'FROZEN_NORMALIZATION_REPAIR_BEFORE_V2_FORWARDS',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'failed_original_job':'130567','failed_original_outputs_preserved':'results/quality',
 'diagnosed_normalization_difference_max':5.960464477539063e-8,'exact_frozen_GPU_normalization':'FP32(uint8) * FP32(1/255)',
 'normalization_helper_sha256':sha(ROOT/'tools/frozen_input.py'),'model_or_calibration_changed':False,
 'diagnostic_sha256':sha(ROOT/'evidence/input_normalization_diagnostic.json'),
 'rerun_reason':'Change evaluated input normalization to exact frozenGPU contract; all old successful validation and partial original PNG files retained; no threshold relaxation.'})
file=ROOT/'protocol/eval_v2.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
execution={'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(file),
 'script_sha256':sha(ROOT/'tools/evaluate_quality_v2.py'),
 'input_and_geometry_hashes':{name:sha(ROOT/name) for name in ['input/validation_images.json','input/event_metrics.py','tools/geometry.py','tools/frozen_input.py']}}
(ROOT/'protocol/execution_v2.json').write_text(json.dumps(execution,indent=2)+'\n')
job=(ROOT/'tools/run.slurm').read_text().replace('evaluate_quality.py','evaluate_quality_v2.py')
(ROOT/'tools/run_v2.slurm').write_text(job,newline='\n')
print(json.dumps({'protocol_v2_sha256':sha(file),'preserve_failed_job':'130567','checkpoint_unchanged':True,'GPU_tensor_gate_relaxed':False}))
