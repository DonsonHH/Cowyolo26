from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile,subprocess,sys
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'pynq_mosaic192_eval_20261030';COMPILE=PROJECT/'pynq_mosaic192_compile_20261030'
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
gate=load(COMPILE/'results/final_review.json');assert gate['actual_board_raw_arrays_byte_exact']==8
ROOT.mkdir(exist_ok=False)
for name in ['tools','input','protocol','results','evidence','logs']:(ROOT/name).mkdir()
old=PROJECT/'pynq_rot192_eval_20261029';q=load(COMPILE/'delivery/results/qualification/summary.json')
p=load(old/'protocol/eval_v2.json')
for name,source in [('input/validation_images.json',old/'input/validation_images.json'),('input/event_metrics.py',old/'input/event_metrics.py'),('tools/geometry.py',old/'tools/geometry.py'),('tools/frozen_input.py',old/'tools/frozen_input.py')]:
    f=ROOT/name;f.write_bytes(source.read_bytes())
text=(old/'tools/evaluate_quality_v2.py').read_text(encoding='utf-8')
text=text.replace('protocol/eval_v2.json','protocol/eval_v1.json').replace('protocol/execution_v2.json','protocol/execution_v1.json')
text=text.replace("ROOT/'results/quality_v2'","ROOT/'results/quality'")
text=text.replace('pynq_rot192_compile_20261029','pynq_mosaic192_compile_20261030')
before="PROJECT/'detector_factorial_20261029/results/evaluation/S192_rot90_seed26_validation_predictions.json.gz'"
after="PROJECT/'mosaic_pair_20261030/results/evaluation_v2/mosaic050_seed26/validation_predictions.json.gz'"
assert text.count(before)==1;text=text.replace(before,after)
before="PROJECT/'factorial_lane_crop_20261029/results/roi'/spec['name']/p['model']/'raw_predictions.json.gz'"
after="PROJECT/'mosaic_pair_20261030/results/evaluation_v2'/p['model']/spec['name']/'raw_predictions.json.gz'"
assert text.count(before)==1;text=text.replace(before,after)
text=text.replace('ROT192_FP32_QDQ_FULL_VALIDATION_TWO_VIDEO_QUALITY_AND8_NATIVE_INTEGER_ANCHORS_COMPLETE','MOSAIC192_FP32_QDQ_FULL_VALIDATION_TWO_VIDEO_QUALITY_AND8_NATIVE_INTEGER_ANCHORS_COMPLETE')
f=ROOT/'tools/evaluate_quality.py';f.write_text(text,encoding='utf-8',newline='\n');ast.parse(text)
for key in ['failed_original_job','failed_original_outputs_preserved','diagnosed_normalization_difference_max','diagnostic_sha256','rerun_reason']:
    p.pop(key,None)
p.update({'status':'FROZEN_BEFORE_FIXED_MOSAIC050192_FP32_QDQ_AND_REAL_VIDEO_INPUT_PREPARATION','created_UTC':datetime.now(timezone.utc).isoformat(),
    'model':'mosaic050_seed26','checkpoint_sha256':q['checkpoint_sha256'],
    'FP32_onnx':REMOTE+'/pynq_mosaic192_compile_20261030/results/qualification/frozen_mosaic050_seed26.onnx','FP32_onnx_sha256':q['FP32_onnx_sha256'],
    'QDQ_onnx':REMOTE+'/pynq_mosaic192_compile_20261030/results/qualification/cow_allconv_int8_normalized.onnx','QDQ_onnx_sha256':q['QDQ_onnx_sha256'],
    'compiled_program':REMOTE+'/pynq_mosaic192_compile_20261030/results/qualification/compiled/program',
    'compiled_graph_sha256':q['graph_sha256'],'resident_plan_sha256':q['resident_plan_sha256'],
    'validation_manifest_sha256':sha(ROOT/'input/validation_images.json'),'normalization_helper_sha256':sha(ROOT/'tools/frozen_input.py'),
    'prior_real_board_training_vector_review_sha256':sha(COMPILE/'results/final_review.json'),
    'prior_GPU_predictions':'all_six_frozen_mosaic_pair_evaluation;primary_seed26_fixed_not_selected_for_source_count',
    'exact_frozen_GPU_normalization':'FP32(uint8)*FP32(1/255);retain8old_crop_tensor_hashes_already_matched_by48_new_GPU_anchors',
    'model_or_calibration_changed_during_evaluation':False,'new_independent_test':False,'whole_goal_complete':False})
save(ROOT/'protocol/eval_v1.json',p)
save(ROOT/'protocol/execution_v1.json',{'protocol_sha256':sha(ROOT/'protocol/eval_v1.json'),'script_sha256':sha(f),
    'input_and_geometry_hashes':{name:sha(ROOT/name) for name in ['input/validation_images.json','input/event_metrics.py','tools/geometry.py','tools/frozen_input.py']}})
plan='''# 固定mosaic0.5主候选：量化质量与完整真实O8视频

前序仅通过8张训练向量的真实板端准入，不能代替本轮。保持checkpoint628db893、原128校准图、192输入、固定裁剪／朝向、conf0.2、ByteTrack与两条计数路径。

1. 以完全相同张量，对1571张开发验证图和2175原片／479Toros源时刻运行FP32／QDQ，共8450次ORT评价；保留全部300候选raw和所有负结果。
2. 2654份视频输入保存为无损192PNG，8锚点在任何新前向前复现冻结GPU张量；8锚点另作原生整数CPU前向，供真实板端对应。固定helper沿用上轮已修正的FP32乘倒数合同。
3. PYNQ上运行全部2654个新权重前向与移植后的跟踪计数，取回raw、事件、阶段耗时及终态；原片0–10873保持历史，仅统计／展示8912–10873。Toros从同一raw缓存形成5／30Hz源采样路径。
4. 该PNG回放不证明相机采集或周期5Hz／后台身份并发，完成后须另外实测。原片12只有人审总量，不填逐事件F1或永久身份准确率；这些材料已经用于开发，不能称独立最终测试。

旧模型与固件保持。新候选是否替换要由本轮实际质量及后续周期负载决定，不能拼接新FP32反向结果与旧实机速度。
'''
(ROOT/'计划与验收.md').write_text(plan,encoding='utf-8')
slurm=f'''#!/bin/bash
#SBATCH --job-name=mosaic192-PTQ-quality
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:12:00
#SBATCH --output={REMOTE}/{ROOT.name}/logs/quality-%j.out
#SBATCH --error={REMOTE}/{ROOT.name}/logs/quality-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONPATH={REMOTE}/pynq_cow_compile_20261029/dependencies:{REMOTE}/deployment_audit/dependencies_offline
cd {REMOTE}/{ROOT.name}
../env/bin/python -B tools/evaluate_quality.py
'''
(ROOT/'tools/quality.slurm').write_text(slurm,encoding='utf-8',newline='\n')
files=[*sorted((ROOT/'input').glob('*')),*sorted((ROOT/'tools').glob('*')),*sorted((ROOT/'protocol').glob('*'))]
a=ROOT/'quality_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for file in files:tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
check=ROOT/'tools/unique_remote.sh';check.write_text('set -euo pipefail\ntest ! -e '+REMOTE+'/'+ROOT.name+'\ntest ! -e '+REMOTE+'/'+ROOT.name+'_quality_inputs_v1.tar.gz\nsqueue -u renly -o "%.18i|%.9P|%.28j|%.8T|%R"\n',encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(check),'--output',str(ROOT/'evidence/remote_unique.txt')],check=True)
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'_quality_inputs_v1.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
a=Path('PHASE_quality_inputs_v1.tar.gz');root=Path('PHASE');assert not root.exists() and hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
PY
sbatch --parsable PHASE/tools/quality.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/submit_quality.sh';f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/submission.txt')],check=True)
