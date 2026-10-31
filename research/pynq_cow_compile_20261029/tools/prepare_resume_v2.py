from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=ROOT/'compiler_workspace';new=ROOT/'compiler_workspace_v2';assert not new.exists();shutil.copytree(old,new)
head=new/'runtime_fast/head_lut.py';text=head.read_text();before=sha(head)
assert "spec['Cout']==80" in text and 'np.array([1,80,-1]' in text
text=text.replace("assert spec['FPGA_supported'] and spec['Cout']==80","assert spec['FPGA_supported'] and spec['Cout'] in (1,80)\n  classes=int(spec['Cout'])").replace('np.array([1,80,-1]','np.array([1,classes,-1]')
head.write_text(text,newline='\n')
source=(ROOT/'tools/compile_old_seed26.py').read_text()
start=source.index("    sys.path.insert(0,str(D/'tools'));from compiler import compile_onnx")
end=source.index("if __name__=='__main__':main()")
tail=source[start:end]
tail=tail.replace("'status':'COMPILED_COW1_CLASS_O8_PIPELINE_QUALIFICATION_COMPLETE'","'status':'COMPILED_COW1_CLASS_O8_PIPELINE_QUALIFICATION_V2_COMPLETE'")
tail=tail.replace("'source_video_Toros_or_validation_pixels_used':False", "'source_video_Toros_or_validation_pixels_used':False,'normalization_runtime_parity':normalization_parity,'old_export_and_calibration_reused_unchanged':True")
prefix='''"""Resume only graph compilation from frozen successful FP32/PTQ assets."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,socket,json,hashlib,shutil,time,subprocess,copy,gc
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np,cv2,torch,onnx,onnxruntime as ort
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'compiler_workspace_v2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):assert not p.exists();p.write_text(json.dumps(obj,indent=2)+'\\n')
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    cv2.setNumThreads(1);torch.set_num_threads(4)
    p=json.loads((ROOT/'protocol/compile_v1.json').read_text());size=p['size'];old=ROOT/'results/qualification'
    resume=json.loads((ROOT/'protocol/compile_resume_v2.json').read_text())
    for row in resume['workspace_files']:assert sha(D/row['relative_file'])==row['sha256']
    checkpoint=old/'frozen_cow_seed26.pt';fp=old/'frozen_cow_seed26.onnx';original=old/'cow_allconv_int8.onnx'
    assert sha(checkpoint)==p['source_checkpoint_sha256'] and len(json.loads((old/'actual_calibration_inputs.json').read_text()))==128
    out=ROOT/'results/qualification_v2';out.mkdir(exist_ok=False)
    save(out/'reuse_gate.json',{'old_job':'130531','old_checkpoint_sha256':sha(checkpoint),'old_FP32_sha256':sha(fp),'old_QDQ_sha256':sha(original),
        'old_calibration_inputs_sha256':sha(old/'actual_calibration_inputs.json'),'new_calibration_or_training_updates':0})
    from normalize_graph import normalize
    source=out/'cow_allconv_int8_normalized.onnx';normalize(original,source,out/'structural_normalization.json')
    sys.path.insert(0,str(D/'runtime'));from board_runtime import preprocess
    options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1;options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    original_session=ort.InferenceSession(str(original),sess_options=options,providers=['CPUExecutionProvider'])
    normalized_session=ort.InferenceSession(str(source),sess_options=options,providers=['CPUExecutionProvider']);normalization_parity=[]
    for row in p['calibration'][:8]:
        image=cv2.imread(row['image_alias']);x=preprocess(np.rot90(image,k=row['orientation_ccw_quarter_turns']).copy(),size)
        before=original_session.run(None,{'images':x})[0];after=normalized_session.run(None,{'images':x})[0]
        assert np.array_equal(before,after)
        normalization_parity.append({'file_name':row['file_name'],'outputs_exact':True,'raw_sha256':hashlib.sha256(before.tobytes()).hexdigest()})
    del original_session,normalized_session;gc.collect()
    save(out/'normalization_parity.json',normalization_parity)
'''
script=ROOT/'tools/resume_compile_v2.py';assert not script.exists();script.write_text(prefix+tail+"if __name__=='__main__':main()\n",newline='\n')
files=[{'relative_file':p.relative_to(new).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(new.rglob('*')) if p.is_file()]
protocol={'status':'FROZEN_AFTER_130531_CLASS_HEAD_SHADOWING_FAILURE_BEFORE_GRAPH_ONLY_RESUME',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'base_protocol_sha256':sha(ROOT/'protocol/compile_v1.json'),
 'workspace_files':files,'normalization_script_sha256':sha(ROOT/'tools/normalize_graph.py'),'resume_script_sha256':sha(script),
 'runtime_fast_class_LUT_original_sha256':before,'runtime_fast_class_LUT_modified_sha256':sha(head),
 'original_inputs_calibration_or_training_changed':False,'new_output':'results/qualification_v2','prior_failed_artifacts_preserved':True,
 'structural_rewrites':'ObservedTileonlyunitdimensions->Expand;observedbatch1onecolumnGather->Reshape/Unsqueeze/GatherElements;exact8trainingORToutputgatebeforecompile.',
 'whole_goal_complete':False}
file=ROOT/'protocol/compile_resume_v2.json';assert not file.exists();file.write_text(json.dumps(protocol,indent=2)+'\n')
slurm=ROOT/'tools/compile_resume_v2.slurm';assert not slurm.exists();slurm.write_text((ROOT/'tools/compile_v2.slurm').read_text().replace('tools/compile_old_seed26.py','tools/resume_compile_v2.py').replace('cow-O8-compile-gate','cow-O8-compile-resume'),newline='\n')
print(json.dumps({'resume_protocol_sha256':sha(file),'workspace_files':len(files),'old_FP32_and_QDQ_reused':True}))
