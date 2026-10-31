"""Clone accepted compiler bytes; bind the already-selected new checkpoint."""
from pathlib import Path
from datetime import datetime,timezone
import ast,json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
for name in ['protocol','input','reference','results','logs','evidence']:(ROOT/name).mkdir(exist_ok=True)
old=PROJECT/'pynq_rot192_compile_20261029';p=load(old/'protocol/compile_v1.json');candidate=load(PROJECT/'mosaic_pair_20261030/results/retained_candidate.json')
assert candidate['name']=='mosaic050_seed26' and candidate['checkpoint_sha256']=='628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb'
assert sha(candidate['local_checkpoint'])==candidate['checkpoint_sha256']
D=ROOT/'compiler_workspace';assert not D.exists();D.mkdir()
for row in p['workspace_files']:
    source=old/'compiler_workspace'/row['relative_file'];assert sha(source)==row['sha256']
    target=D/row['relative_file'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(source.read_bytes())
for name in ['ordered_float_reference.py','ordered_hybrid_executor.py']:
    source=PROJECT/'pynq_o8_sizes_20261030/tools'/name;target=ROOT/'reference'/name;assert not target.exists();target.write_bytes(source.read_bytes())
normal=ROOT/'tools/normalize_graph.py';assert not normal.exists();normal.write_bytes((old/'tools/normalize_graph.py').read_bytes())
expected=old/'delivery/results/qualification/actual_calibration_inputs.json';save(ROOT/'input/expected_calibration.json',load(expected))
text=(old/'tools/compile_rot192.py').read_text(encoding='utf-8')
text=text.replace('frozen_S192_rot90_seed26.pt','frozen_mosaic050_seed26.pt')
needle="    for r in p['workspace_files']:assert sha(D/r['relative_file'])==r['sha256']"
addition="""    expected_calibration=json.loads((ROOT/'input/expected_calibration.json').read_text())
    assert len(expected_calibration)==128 and sha(ROOT/'input/expected_calibration.json')==p['expected_calibration_records_sha256']
    for name,digest in p['ordered_reference_files'].items():assert sha(ROOT/name)==digest
"""
assert text.count(needle)==1;text=text.replace(needle,addition+needle)
needle="            self.records.append({'file_name':row['file_name'],'sha256':row['sha256'],'orientation_ccw_quarter_turns':row['orientation_ccw_quarter_turns'],"
replacement="""            prior=expected_calibration[self.index]
            assert row['file_name']==prior['file_name'] and row['orientation_ccw_quarter_turns']==prior['orientation_ccw_quarter_turns']
            assert hashlib.sha256(tensor.tobytes()).hexdigest()==prior['input_tensor_sha256']
"""+needle
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle="    sys.path.insert(0,str(D/'pc_intdw'));from hybrid_executor import YOLOHybridExecutor"
replacement="""    sys.path.insert(0,str(D/'pc_intdw'));from hybrid_executor import YOLOHybridExecutor as LegacyExecutor
    sys.path.insert(0,str(ROOT/'reference'));from ordered_hybrid_executor import YOLOHybridExecutor
    from ordered_float_reference import contract_toys
    ordered_toys=contract_toys()"""
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle="    reference=YOLOHybridExecutor(M,TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)"
assert text.count(needle)==1;text=text.replace(needle,needle+"\n    legacy=LegacyExecutor(M,TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)")
needle="    float_session=ort.InferenceSession(str(fp),sess_options=so,providers=['CPUExecutionProvider']);vectors=[];maximum_box=maximum_score=0."
assert text.count(needle)==1;text=text.replace(needle,needle+"\n    qdq_session=ort.InferenceSession(str(source),sess_options=so,providers=['CPUExecutionProvider'])")
needle="        ref=reference.run(x).copy();actual=nativegraph.run(x).copy();fpraw=float_session.run(None,{'images':x})[0]"
assert text.count(needle)==1;text=text.replace(needle,needle+"\n        legacyraw=legacy.run(x).copy();qdqraw=qdq_session.run(None,{'images':x})[0]")
needle="np.savez_compressed(out/('parity_train_'+str(i)+'.npz'),input=x,reference_integer_raw=ref,native_integer_raw=actual,FP32_raw=fpraw)"
replacement="np.savez_compressed(out/('parity_train_'+str(i)+'.npz'),input=x,reference_integer_raw=ref,native_integer_raw=actual,legacy_numpy_integer_raw=legacyraw,FP32_raw=fpraw,QDQ_raw=qdqraw)"
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle="'maximum_score_error':score_error,'classes_exact':True,'passes':box_error<=.002 and score_error<=.0001}"
replacement="'maximum_score_error':score_error,'classes_exact':True,'primary_full_raw_bytes_exact':ref.tobytes()==actual.tobytes(),'legacy_full_raw_bytes_exact':legacyraw.tobytes()==actual.tobytes(),'legacy_maximum_box_error':float(np.max(np.abs(legacyraw[:,:,:4]-actual[:,:,:4]))),'legacy_maximum_score_error':float(np.max(np.abs(legacyraw[:,:,4]-actual[:,:,4]))),'passes':box_error<=.002 and score_error<=.0001}"
assert text.count(needle)==1;text=text.replace(needle,replacement)
text=text.replace('del nativegraph,reference,float_session','del nativegraph,reference,legacy,float_session,qdq_session')
text=text.replace('PRESELECTED_ROT192_COW_O8_COMPILE_AND_CPU_PARITY_COMPLETE','MOSAIC050_SEED26_O8_COMPILE_ORDERED_AND_LEGACY_CPU_PARITY_COMPLETE')
needle="'all_native_CPU_parity_gates_pass':all(v['passes'] for v in vectors),'new_training_updates':0,"
replacement="'ordered_reference_contract_toys':ordered_toys,'all128_calibration_tensors_exact_to_old':True,'primary_ordered_vectors_byte_exact':sum(v['primary_full_raw_bytes_exact'] for v in vectors),'legacy_numpy_vectors_byte_exact':sum(v['legacy_full_raw_bytes_exact'] for v in vectors),"+needle
assert text.count(needle)==1;text=text.replace(needle,replacement)
script=ROOT/'tools/compile_mosaic192.py';assert not script.exists();script.write_text(text,encoding='utf-8',newline='\n');ast.parse(text)
p.update({'status':'FROZEN_BEFORE_MOSAIC050_SEED26_EXPORT_PTQ_OR_COMPILATION','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'source_checkpoint':candidate['remote_checkpoint'],'source_checkpoint_sha256':candidate['checkpoint_sha256'],'primary_model':candidate['name'],
    'new_factorial_weights_used':False,'new_mosaic_pair_weights_used':True,'compiler_source_phase':'pynq_rot192_compile_20261029',
    'previous_successful_compile_review_sha256':sha(old/'results/final_review.json'),
    'current_training_phase_review_sha256':sha(PROJECT/'mosaic_pair_20261030/results/final_review.json'),
    'retained_candidate_record_sha256':sha(PROJECT/'mosaic_pair_20261030/results/retained_candidate.json'),
    'selection_rule':'keep_preselected_primary_seed26;not_seed28_despite_source11;single_fixed_mosaic050_development_candidate',
    'primary_selection_protocol_sha256':sha(PROJECT/'mosaic_pair_20261030/protocol/training_v1.json'),
    'compile_script_sha256':sha(script),'normalization_script_sha256':sha(normal),
    'expected_calibration_records_sha256':sha(ROOT/'input/expected_calibration.json'),
    'ordered_reference_files':{f.relative_to(ROOT).as_posix():sha(f) for f in sorted((ROOT/'reference').glob('*.py'))},
    'primary_reference_contract':'explicit_FP32_nonconv_MatMul_serial_products_and_sum_noFMA;Softmax_scalar_C99expf_serial_FP32sum_division',
    'primary_reference_rule_frozen_before_any_new_model_parity_result':True,
    'legacy_numpy_reference_saved_separately_and_not_rewritten':True,'native_engine_compiler_or_firmware_changed':False,
    'background_identity_added':False,'board_inference_in_this_stage':False,'whole_goal_complete':False})
save(ROOT/'protocol/compile_v1.json',p)
slurm=(old/'tools/compile.slurm').read_text(encoding='utf-8').replace('pynq_rot192_compile_20261029','pynq_mosaic192_compile_20261030').replace('compile_rot192.py','compile_mosaic192.py').replace('rot192-O8-compile','mosaic192-O8-compile')
f=ROOT/'tools/compile.slurm';assert not f.exists();f.write_text(slurm,encoding='utf-8',newline='\n')
files=[*sorted(p for p in D.rglob('*') if p.is_file()),*sorted((ROOT/'reference').glob('*.py')),ROOT/'input/expected_calibration.json',script,normal,f,ROOT/'protocol/compile_v1.json']
a=ROOT/'compile_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for file in files:tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
save(ROOT/'evidence/compiler_input_staging.json',{'archive_bytes':a.stat().st_size,'archive_sha256':sha(a),'members':len(files),'compiler_workspace_bytes_unchanged_files':len(p['workspace_files'])})
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
check=ROOT/'tools/unique_remote.sh';assert not check.exists();check.write_text('set -euo pipefail\ntest ! -e '+REMOTE+'/'+ROOT.name+'\ntest ! -e '+REMOTE+'/'+ROOT.name+'_compile_inputs_v1.tar.gz\nsqueue -u renly -o "%.18i|%.9P|%.28j|%.8T|%R"\n',encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(check),'--output',str(ROOT/'evidence/remote_unique.txt')],check=True)
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'_compile_inputs_v1.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json
a=Path('PHASE_compile_inputs_v1.tar.gz');root=Path('PHASE');assert not root.exists() and hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
p=json.loads((root/'protocol/compile_v1.json').read_text())
for r in p['workspace_files']:assert hashlib.sha256((root/'compiler_workspace'/r['relative_file']).read_bytes()).hexdigest()==r['sha256']
assert hashlib.sha256(Path(p['source_checkpoint']).read_bytes()).hexdigest()==p['source_checkpoint_sha256']
print('SAME60_COMPILER_FILES128_TRAIN_INPUTS_ORDERED_PRIMARY_AND_LEGACY_REFERENCE_FROZEN')
PY
sbatch --parsable PHASE/tools/compile.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/submit_compile.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/submission.txt')],check=True)
