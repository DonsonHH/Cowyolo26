"""Freeze the preselected low-resolution model and an isolated O8 compiler."""
from pathlib import Path
from datetime import datetime, timezone
import json, hashlib, shutil, py_compile
PROJECT=Path(__file__).resolve().parents[2]
OLD=PROJECT/'pynq_cow_compile_20261029'
ROOT=PROJECT/'pynq_rot192_compile_20261029'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8'))
ROOT.mkdir(exist_ok=False)
for d in ['tools','protocol','evidence','results']: (ROOT/d).mkdir()
source=OLD/'compiler_workspace_v2'
destination=ROOT/'compiler_workspace'
for file in source.rglob('*'):
    if not file.is_file() or file.suffix in ['.so','.pyc'] or '__pycache__' in file.parts: continue
    target=destination/file.relative_to(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(file,target)
workspace=[{'relative_file':p.relative_to(destination).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(destination.rglob('*')) if p.is_file()]
assert len(workspace)==60
crop=load(PROJECT/'factorial_lane_crop_20261029/protocol/crop_v1.json')
primary=crop['primary_case_for_media_not_count_selection']
assert primary=='S192_rot90_seed26'
model=next(m for m in crop['models'] if m['name']==primary)
p=load(OLD/'protocol/compile_v1.json')
p.update({'status':'FROZEN_BEFORE_PRESELECTED_ROT192_EXPORT_OR_PTQ',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'primary_model':primary,
 'source_checkpoint':model['checkpoint'],'source_checkpoint_sha256':model['sha256'],
 'new_factorial_weights_used':True,'workspace_files':workspace,
 'compiler_source_phase':'pynq_cow_compile_20261029/compiler_workspace_v2',
 'previous_successful_compile_review_sha256':sha(OLD/'results/final_review.json'),
 'selection_rule':'Keep192rot90seed26preselectedbeforecropresults;notchoosecount12seed.',
 'primary_selection_protocol_sha256':sha(PROJECT/'factorial_lane_crop_20261029/protocol/crop_v1.json'),
 'current_crop_phase_review_sha256':sha(PROJECT/'factorial_lane_crop_20261029/results/final_review.json'),
 'calibration_reuses_exact_128_train_images_and_orientations':True,
 'training_or_calibration_on_source_Toros_or_validation':False,
 'expected_O8_bit_sha256':'5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8',
 'normalization_rule':'UnitTile->Expandandfixed300x1Gather->GatherElements,unchangedarithmetic;8trainoutputsbyteexactrequired.'})
text=(OLD/'tools/compile_old_seed26.py').read_text(encoding='utf-8')
text=text.replace('Frozen existing cow weights -> train-only PTQ -> O8 graph -> CPU parity.',
 'PreselectedS192rot90seed26 -> train-only PTQ -> verifiedO8 compiler -> CPU parity.')
text=text.replace('frozen_cow_seed26','frozen_S192_rot90_seed26')
marker="    print('QUANTIZATION_COMPLETE_BEFORE_O8_COMPILE',flush=True)"
assert text.count(marker)==1
new=marker+'''
    original=source;source=out/'cow_allconv_int8_normalized.onnx'
    from normalize_graph import normalize
    normalize(original,source,out/'structural_normalization.json')
    options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    before_session=ort.InferenceSession(str(original),sess_options=options,providers=['CPUExecutionProvider'])
    after_session=ort.InferenceSession(str(source),sess_options=options,providers=['CPUExecutionProvider'])
    normalization_parity=[]
    for row in p['calibration'][:8]:
        image=cv2.imread(row['image_alias']);x=preprocess(np.rot90(image,k=row['orientation_ccw_quarter_turns']).copy(),size)
        before=before_session.run(None,{'images':x})[0];after=after_session.run(None,{'images':x})[0]
        assert before.tobytes()==after.tobytes()
        normalization_parity.append({'file_name':row['file_name'],'outputs_byte_exact':True,'raw_sha256':hashlib.sha256(before.tobytes()).hexdigest()})
    del before_session,after_session;gc.collect()
    save(out/'normalization_parity.json',normalization_parity)
'''
text=text.replace(marker,new)
text=text.replace("'COMPILED_COW1_CLASS_O8_PIPELINE_QUALIFICATION_COMPLETE'","'PRESELECTED_ROT192_COW_O8_COMPILE_AND_CPU_PARITY_COMPLETE'")
text=text.replace("'actual_train_calibration_images':128,'class_count':1,","'actual_train_calibration_images':128,'class_count':1,'primary_model':p['primary_model'],'normalization_parity':normalization_parity,")
(ROOT/'tools/compile_rot192.py').write_text(text,encoding='utf-8',newline='\n')
shutil.copyfile(OLD/'tools/normalize_graph.py',ROOT/'tools/normalize_graph.py')
p['compile_script_sha256']=sha(ROOT/'tools/compile_rot192.py')
p['normalization_script_sha256']=sha(ROOT/'tools/normalize_graph.py')
(ROOT/'protocol/compile_v1.json').write_text(json.dumps(p,indent=2)+'\n')
py_compile.compile(str(ROOT/'tools/compile_rot192.py'),doraise=True)
remote='/share/home/renly/projects/idcoo_research_20261026'
job=f'''#!/bin/bash
#SBATCH --job-name=rot192-O8-compile
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:12:00
#SBATCH --output={remote}/{ROOT.name}/logs/compile-%j.out
#SBATCH --error={remote}/{ROOT.name}/logs/compile-%j.err
set -euo pipefail
cd {remote}/{ROOT.name}
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export YOLO_AUTOINSTALL=false
export PYTHONPATH={remote}/pynq_cow_compile_20261029/dependencies:{remote}/deployment_audit/dependencies_offline
../env/bin/python tools/compile_rot192.py
'''
(ROOT/'tools/compile.slurm').write_text(job,newline='\n')
(ROOT/'计划与验收.md').write_text('''# 固定192直角候选的O8量化与上板准入

模型固定为新S192_rot90_seed26，来自裁剪评价前的选择；不按开发片数到12挑模型。原12头640版本保持。

1. 复制已通过8真实板上向量的O8编译源码，隔离新目录；仅使用128张训练图做MinMax校准，训练和校准均不接触原片、Toros或验证集像素。
2. 导出固定192单类模型。逐字节核对8张训练图的结构归一化前后输出，再将94个卷积交给PL、8个深度卷积交给ARM，核对完整整数参考与原生C++执行。
3. 编译合格后在同一O8固件上实际运行新模型，验证输出与CPU参考以及延迟；训练向量合格只说明实现可执行。
4. 另用固定视频和验证集检查FP32→量化→原生整数差异，保持原图坐标及既有跟踪计数。移植跟踪程序先以原缓存逐时刻回归，再在板上执行。
5. 最终仍需输入采集、真实板上计数和后台身份联合运行。每一步保留失败、原始输出和未达成项，不能将张量推理速度称为整个系统5FPS。

本文件写于本模型首次量化之前；提交与实测记录另存evidence和results。
''',encoding='utf-8')
print(json.dumps({'phase':str(ROOT),'workspace_files':len(workspace),'primary_model':primary,'checkpoint_sha256':model['sha256'],'protocol_sha256':sha(ROOT/'protocol/compile_v1.json'),'new_training_updates':0}))
