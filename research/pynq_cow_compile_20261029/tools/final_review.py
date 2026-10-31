from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=load(ROOT/'results/independent_implementation_verification.json');strict=load(ROOT/'results/strict_raw_bytes_verification.json')
assert v['status']=='SINGLE_CLASS_O8_COMPILE_STATIC_GRAPH_CLASS_LUT_AND8_ACTUAL_FPGA_ARM_VECTORS_INDEPENDENTLY_VERIFIED'
assert v['class_count']==1 and v['size']==192 and v['dense_PL_convolutions']==94 and v['integer_ARM_depthwise']==8
assert v['static_tensor_entries_parsed']==2132 and v['static_nodes_parsed']==383 and v['graph_binary_bytes_parsed']==14605169
assert v['class_LUT_codes_scalar_checked']==768 and v['maximum_LUT_scalar_sigmoid_difference']<2e-7
assert v['generalized80class_LUT_metadata_contract_matches_original'] is True and v['80class_test_is_LUT_contract_not_full_network_execution'] is True
assert v['CPU_reference_vs_native_vectors_exact']==v['actual_FPGA_ARM_reference_vectors_checked']==8 and v['actual_model_forwards_with2warmups']==10
assert v['board_maximum_box_error']==v['board_maximum_score_error']==0 and v['actual_board_raw_arrays_byte_exact'] is True
assert strict['status']=='ALL8_CPU_REFERENCE_NATIVE_AND_REAL_BOARD_RAW_BYTES_EXACT_INCLUDING_SIGNED_ZERO' and len(strict['arrays'])==8
assert v['training_vector_detections_above_conf02']==[1,1,1,0,2,1,1,0]
assert v['current15_new_training_models_deployed'] is False and v['real_source_video_count_or_identity_accuracy_admitted'] is False
assert v['new_firmware_programming'] is False and v['original_O8_assets_modified'] is False
assert v['foreground_background_joint5FPS_proven'] is False and v['whole_goal_complete'] is False
q=ROOT/'delivery/results/qualification_v2';s=load(q/'summary.json');normal=load(q/'structural_normalization.json')
assert s['checkpoint_sha256']==v['model_checkpoint_sha256']=='51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74'
assert s['actual_train_calibration_images']==128 and s['resident_pairs']==25 and len(s['normalization_runtime_parity'])==8
assert normal['weight_and_quantization_initializer_bytes_modified'] is False and len(normal['changes'])==3
assert normal['normalized_sha256']==sha(q/'cow_allconv_int8_normalized.onnx')
reuse=load(q/'reuse_gate.json');original=ROOT/'delivery/results/qualification'
assert sha(original/'cow_allconv_int8.onnx')==reuse['old_QDQ_sha256']==normal['source_sha256']
assert sha(original/'frozen_cow_seed26.onnx')==reuse['old_FP32_sha256'] and sha(original/'actual_calibration_inputs.json')==reuse['old_calibration_inputs_sha256']
runtime=load(ROOT/'evidence/final_O8_runtime_read.json');assert runtime['exit_code']==0;board=load(ROOT/'board_delivery/final_state.json')
fresh=json.loads(runtime['stdout']);assert fresh['prior_cow_PID12010_exists'] is False and fresh['services']=='active\nactive\n'
release=load(ROOT/'source_snapshot/release_manifest.json');oldhash={r['path']:r['sha256'] for r in release['runtime_files']}
for row in fresh['actual_runtime_files']:
    assert oldhash[row['relative']]==row['sha256']
assert board['PL_bit_sha256']=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
for archive,record in [('qualification_delivery.tar.gz','qualification_transfer.json'),('board_results.tar.gz','board_transfer.json'),('board_vectors_payload.tar.gz','board_payload_staging.json')]:
    r=load(ROOT/'evidence'/record);assert sha(ROOT/archive)==r['sha256'] and (ROOT/archive).stat().st_size==r['bytes']
assert '130531|cow-O8-compile-gate|FAILED|1:0|' in (ROOT/'evidence/compile_status01.txt').read_text()
assert '130539|cow-O8-compile-resume|COMPLETED|0:0|' in (ROOT/'evidence/resume_v2_status01.txt').read_text()
frozen=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';assert sha(frozen)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
retained={frozen.relative_to(PROJECT).as_posix():sha(frozen)};accepted=load(frozen)
for key,hk in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
    file=Path(accepted[key]);assert sha(file)==accepted[hk];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
file=Path(accepted['source_event_record']['events_path']);assert sha(file)==accepted['source_event_record']['events_sha256'] and len(load(file))==12;retained[file.relative_to(PROJECT).as_posix()]=sha(file)
training_freeze=load(PROJECT/'detector_factorial_20261029/evidence/all_checkpoints_frozen.json')
assert len(training_freeze['conditions'])==15 and training_freeze['total_formal_optimizer_updates']==18375
docs=[ROOT/'计划与验收.md',ROOT/'奶牛单类权重O8实机准入.md',ROOT/'Review与当前状态.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
links=[]
for doc in docs:
    text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
    for m in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',text):
        link=m.group(1) or m.group(2)
        if link.startswith(('http://','https://','#')):continue
        file=Path(unquote(link.split('#')[0]));file=file if file.is_absolute() else doc.parent/file
        assert file.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
evidence=['protocol/compile_v1.json','protocol/compile_resume_v2.json','protocol/board_vectors_v1.json',
 'evidence/archive_source_inspection.json','evidence/compiler_modifications_v1.json','results/independent_implementation_verification.json',
 'results/strict_raw_bytes_verification.json','results/qualification_transfer_verification.json','evidence/compile_status01.txt',
 'evidence/resume_v2_status01.txt','evidence/board_vectors_launch.json','evidence/final_O8_runtime_read.json',
 'delivery/results/qualification_v2/summary.json','delivery/results/qualification_v2/normalization_parity.json',
 'delivery/results/qualification_v2/reuse_gate.json','delivery/results/qualification_v2/structural_normalization.json',
 'delivery/results/qualification_v2/compiled/program/program.json','delivery/results/qualification_v2/compiled/program/graph.bin',
 'delivery/results/qualification_v2/resident_plan_all/resident_plan.bin','board_delivery/results/record.json','board_delivery/results/terminal.json','board_delivery/final_state.json']
result={'status':'COW1_CLASS192_O8_NATIVE_COMPILE_AND8_REAL_BOARD_VECTORS_REVIEWED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'implementation_qualification_phase_complete':True,'whole_goal_complete':False,
 'user_confirmed_O8_engine':True,'model_checkpoint_sha256':s['checkpoint_sha256'],'class_count':1,'input_size':192,
 'train_only_PTQ_calibration_images':128,'static_graph_nodes':383,'static_tensors':2132,'graph_bytes':14605169,
 'PL_integer_convolutions':94,'ARM_integer_depthwise':8,'resident_pairs':25,'exact_structure_rewrite_count':3,
 'original_and_normalized_ONNX_training_vectors_exact':8,'CPU_reference_and_native_training_vectors_exact':8,
 'actual_PYNQ_FPGA_ARM_training_vectors_exact':8,'actual_board_model_forwards_with2warmups':10,'strict_raw_byte_arrays_exact':8,
 'class_LUT_scalar_code_checks':768,'maximum_scalar_sigmoid_delta':v['maximum_LUT_scalar_sigmoid_difference'],
 'board_maximum_box_error':0,'board_maximum_score_error':0,'training_vector_tensor_to_raw_mean_ms':v['mean_training_vector_tensor_to_raw_ms'],
 'new_firmware_programmed':False,'original_O8_runtime_and_firmware_hashes_preserved':True,'board_process_terminal_and_absent':True,
 'old_seed26_qualifier_not_new15_models':True,'new15_lowres_models_deployed':False,
 'real_source_video_count_accuracy_admitted':False,'camera_active':False,'background_identity_active':False,
 'foreground_background_joint5FPS_proven':False,'new_training_updates_in_this_compile_phase':0,'new_independent_test':False,
 'original_human12_milestone_preserved':True,'retained_artifact_hashes':retained,
 'evidence_hashes':{r:sha(ROOT/r) for r in evidence},'documents':[{'path':str(d.resolve()),'sha256':sha(d)} for d in docs],
 'local_links_checked':len(links),'manual_numeric_scope_and_implementation_review_completed':True,'new_figures_or_videos_generated':0}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['retained_artifact_hashes','evidence_hashes','documents']}))
