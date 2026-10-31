from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,py_compile,tarfile
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'pynq_o8_sizes_20261030';ROOT.mkdir(exist_ok=False)
for d in ['tools','protocol','results','evidence']:(ROOT/d).mkdir()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
previous=PROJECT/'pynq_rot192_compile_20261029';base=load(previous/'protocol/compile_v1.json')
models=load(PROJECT/'factorial_lane_crop_20261029/protocol/crop_v1.json')['models'];records=[]
for size in [256,320]:
 case=ROOT/('s'+str(size));case.mkdir()
 for d in ['protocol','tools','results','logs']:(case/d).mkdir()
 destination=case/'compiler_workspace'
 for file in (previous/'compiler_workspace').rglob('*'):
  if not file.is_file() or file.suffix in ['.pyc','.so'] or '__pycache__' in file.parts:continue
  target=destination/file.relative_to(previous/'compiler_workspace');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
 files=[{'relative_file':p.relative_to(destination).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(destination.rglob('*')) if p.is_file()];assert len(files)==60
 model=next(r for r in models if r['name']==f'S{size}_rot90_seed26')
 p=dict(base);p.update({'status':'FROZEN_BEFORE_ADDITIONAL_SAME_O8_SIZE_QUALIFICATION','created_UTC':datetime.now(timezone.utc).isoformat(),
  'size':size,'primary_model':model['name'],'source_checkpoint':model['checkpoint'],'source_checkpoint_sha256':model['sha256'],
  'workspace_files':files,'same_O8_size_control':True,'selection_rule':'Fixedseed26at256and320;allhardwarecasesretained;nochooseusingcounts.',
  'previous192_actual_video_review_sha256':sha(PROJECT/'pynq_rot192_eval_20261029/results/final_review.json'),
  'calibration_reuses_exact_128_train_images_and_orientations':True,'all128_resized_at_this_fixed_size':True,
  'new_detector_training':False,'legacy_O6_comparison_replaced_in_current_size_control_only':True,
  'board_forward_in_this_compile_stage':False,'whole_goal_complete':False})
 text=(previous/'tools/compile_rot192.py').read_text();text=text.replace("assert size==192 and p['pipeline_qualification_only'] is True","assert size in [256,320] and p['pipeline_qualification_only'] is True")
 text=text.replace('frozen_S192_rot90_seed26','frozen_S'+str(size)+'_rot90_seed26').replace('PRESELECTED_ROT192_COW_O8_COMPILE_AND_CPU_PARITY_COMPLETE','FIXED_SAME_O8_SIZE_COW_COMPILE_AND_CPU_PARITY_COMPLETE')
 file=case/'tools/compile_fixed_size.py';file.write_text(text,newline='\n');py_compile.compile(str(file),doraise=True)
 shutil.copyfile(previous/'tools/normalize_graph.py',case/'tools/normalize_graph.py')
 p['compile_script_sha256']=sha(file);p['normalization_script_sha256']=sha(case/'tools/normalize_graph.py')
 proto=case/'protocol/compile_v1.json';proto.write_text(json.dumps(p,indent=2)+'\n')
 records.append({'size':size,'case':'s'+str(size),'protocol_sha256':sha(proto),'checkpoint_sha256':model['sha256']})
protocol={'status':'FROZEN_BEFORE_TWO_SAME_O8_SIZE_COMPILE_JOBS','created_UTC':datetime.now(timezone.utc).isoformat(),'cases':records,
 'engine':'userconfirmed yolo26_optimization_8','same_bit_sha256':'5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8',
 'context':'Prior256O8and320O6COCOprofilenotapples-to-apples. Theseare256/320newcowmodelswithsameO8,samecompiler,train-onlyPTQ,first8trainingqualificationvectors.',
 'real_video_count_at_additional_sizes_not_proven_by_train_vectors':True,'each_new_case_is_separate_from192_primary':True,'whole_goal_complete':False}
(ROOT/'protocol/sizes_v1.json').write_text(json.dumps(protocol,indent=2)+'\n')
remote='/share/home/renly/projects/idcoo_research_20261026'
job=f'''#!/bin/bash
#SBATCH --job-name=cow-same-O8-sizes
#SBATCH --partition=cu
#SBATCH --array=0-1%2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:12:00
#SBATCH --output={remote}/{ROOT.name}/logs/compile-%A_%a.out
#SBATCH --error={remote}/{ROOT.name}/logs/compile-%A_%a.err
set -euo pipefail
case "$SLURM_ARRAY_TASK_ID" in
 0) fixed_case=s256 ;;
 1) fixed_case=s320 ;;
 *) exit 91 ;;
esac
cd {remote}/{ROOT.name}/"$fixed_case"
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export YOLO_AUTOINSTALL=false
export PYTHONPATH={remote}/pynq_cow_compile_20261029/dependencies:{remote}/deployment_audit/dependencies_offline
../../env/bin/python -B tools/compile_fixed_size.py
'''
(ROOT/'tools/compile.slurm').write_text(job,newline='\n')
(ROOT/'计划与验收.md').write_text('''# 192／256／320对齐用户O8引擎

用户确认原约5FPS基于yolo26_optimization_8。此前板端192／256使用O8，320使用O6，因此单看该三尺寸速度不能归因于分辨率。

保持已预选192主候选和所有原证据，补充固定256／320直角seed26的O8编译与真实板上向量资格检查。三者使用同一O8固件、相同编译源码、128张训练校准图及方向日程和单类头；不同尺寸对应各自预先训练且冻结的权重，不能当作同一权重的纯输入尺寸消融。

先检查完整CPU整数与原生实现，确认内存预算；再按尺寸顺序在同一块板上运行2预热＋8资格向量并及时释放。若资源不足或速度较慢，保留结果而不替换O6历史记录。训练向量只能说明实现及受控延迟，不替代完整视频计数／5Hz周期或同板身份并发。
''',encoding='utf-8')
print(json.dumps({'phase':str(ROOT),'cases':records,'workspace_files_each':60,'new_training_updates':0}))
