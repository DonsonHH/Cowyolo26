"""Freeze all choices and code before the first new inference."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,subprocess,sys,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def copy(src,dest):assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(src.read_bytes())
for name in ['protocol','input','results','evidence','logs']:(ROOT/name).mkdir(exist_ok=True)
oldroot=PROJECT/'pynq_rot192_eval_20261029'
q=load(oldroot/'protocol/eval_v2.json')
port=load(PROJECT/'pynq_frontend_port_20261029/regression_v1.json')
for name in ['validation_images.json','geometry.py','event_metrics.py']:
    source=oldroot/'input'/name if name!='geometry.py' else oldroot/'tools/geometry.py'
    copy(source,ROOT/'input'/name)
copy(oldroot/'tools/frozen_input.py',ROOT/'input/frozen_input.py')
external=[]
def bind(local,remote):external.append({'path':str(remote),'sha256':sha(local)})
for name in ['FP32','QDQ']:
    qual=PROJECT/'pynq_rot192_compile_20261029/delivery/results/qualification'
    # The export files were not collected in the small board result package;
    # their immutable exact hashes are the prior protocol's audited source.
    external.append({'path':q[name+'_onnx'],'sha256':q[name+'_onnx_sha256']})
for row in port['files']:
    bind(PROJECT/'pynq_frontend_port_20261029'/row['file'],REMOTE+'/pynq_frontend_port_20261029/'+row['file'])
prior_local=oldroot/'delivery/results/quality_v2'
prior_remote=REMOTE+'/pynq_rot192_eval_20261029/results/quality_v2'
for name in ['summary.json','validation_all_raw.npz','original_all_raw.npz','toros_all_raw.npz','board_input_manifest.json']:
    bind(prior_local/name,prior_remote+'/'+name)
for v in q['videos']:
    for mode in ['FP32','QDQ']:
        folder=Path(v['name'])/mode
        bind(prior_local/folder/'raw_predictions.json.gz',prior_remote+'/'+folder.as_posix()+'/raw_predictions.json.gz')
        for stride in v['counter_replay_strides']:
            name='stride'+str(stride)+'_counter_trace.json.gz'
            bind(prior_local/folder/name,prior_remote+'/'+folder.as_posix()+'/'+name)
p={'status':'FROZEN_THREE_PHOTOMETRIC_CONDITIONS_BEFORE_ANY_NEW_FORWARD','created_host_UTC':datetime.now(timezone.utc).isoformat(),
   'model':q['model'],'checkpoint_sha256':q['checkpoint_sha256'],'size':192,
   'conditions':['none','gamma07','clahe_y2'],
   'transform_scope':'after_linear_resize_at_content192_before_114_padding_no_geometry_change',
   'fixed_gamma':.7,'gamma_quantization':'float64_formula_numpy_rint_to_uint8_LUT256_all_BGR_channels',
   'CLAHE':{'color':'YCrCb_Y_only','clipLimit':2.,'tileGridSize':[8,8]},
   'conditions_selected_using_development_missing_case_not_independent_preregistration':True,
   'parameter_grid_search':False,'parameter_changes_after_outcomes':False,
   'prior_quality_remote':prior_remote,'videos':q['videos'],'tracker_config':port['tracker_config'],'counter_kwargs':q['counter_kwargs'],
   'prediction_confidence':.2,'IoU_matching':.5,'original_human_total':12,'original_human_event_GT':False,
   'original_display_frames_inclusive':[8912,10873],'validation_images':1571,'validation_references':1864,
   'expected_total_ORT_forwards':25350,'expected_counter_paths':36,'expected_tracker_observation_ticks':16404,
   'baseline_expected_exact_raw_arrays':8450,'baseline_expected_exact_video_inputs':2654,
   'frozen_external_files':external,'new_training_updates':0,'actual_board_actions':0,
   'new_independent_test':False,'final_holdout_read':False,'whole_goal_complete':False}
for k in ['FP32_onnx','QDQ_onnx']:p[k]=q[k]
save(ROOT/'protocol/study_v1.json',p)
script='''#!/bin/bash
#SBATCH --job-name=photometric-192
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:25:00
#SBATCH --output=REMOTE/PHASE/logs/study-%j.out
#SBATCH --error=REMOTE/PHASE/logs/study-%j.err
set -euo pipefail
cd REMOTE/PHASE
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONPATH=REMOTE/pynq_cow_compile_20261029/dependencies:REMOTE/deployment_audit/dependencies_offline
../env/bin/python -B tools/run_study.py
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name)
slurm=ROOT/'tools/run.slurm';assert not slurm.exists();slurm.write_text(script,encoding='utf-8',newline='\n')
files=[ROOT/'tools/run_study.py',ROOT/'tools/photometric.py',slurm,*sorted((ROOT/'input').glob('*'))]
for file in files:
    if file.suffix=='.py':ast.parse(file.read_text(encoding='utf-8'))
save(ROOT/'protocol/execution_v1.json',{'created_host_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/study_v1.json'),
    'files_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in files}})
archive=ROOT/'inputs_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in [*files,ROOT/'protocol/study_v1.json',ROOT/'protocol/execution_v1.json']:
        tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
preflight=ROOT/'tools/check_remote_unique.sh'
assert not preflight.exists()
preflight.write_text('set -euo pipefail\ntest ! -e '+REMOTE+'/'+ROOT.name+'\ntest ! -e '+REMOTE+'/'+ROOT.name+'_inputs_v1.tar.gz\nsqueue -u renly -o "%.18i|%.9P|%.28j|%.8T|%R"\n',encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(preflight),'--output',str(ROOT/'evidence/remote_unique_preflight.txt')],check=True)
subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/'+ROOT.name+'_inputs_v1.tar.gz'],check=True)
submit='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
archive=Path('PHASE_inputs_v1.tar.gz');root=Path('PHASE')
assert not root.exists() and hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
root.mkdir()
with tarfile.open(archive) as tar:
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  target=(root/member.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
for name in ['logs','evidence','results']:(root/name).mkdir(exist_ok=True)
print('STAGED_AND_SHA_VERIFIED_BEFORE_SUBMISSION')
PY
sbatch --parsable PHASE/tools/run.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('DIGEST',sha(archive))
file=ROOT/'tools/submit_generated.sh';assert not file.exists();file.write_text(submit,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/submission.txt')],check=True)
save(ROOT/'results/input_staging.json',{'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'baseline_regression_required_before_new_transforms':True})
