from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
profile=load(ROOT/'results/independent_profile_verification.json');inp=load(ROOT/'results/independent_input_verification.json')
jpeg=load(ROOT/'results/independent_stream_verification.json');bank=load(ROOT/'results/independent_framebank_verification.json');board=load(ROOT/'results/final_board_state.json')
assert profile['hardware_image_forwards_supported']==103 and profile['formal_samples_verified']==96 and profile['raw_arrays_verified']==97
assert profile['fixed_E010_raw_repeats_exact']==60 and profile['prior_interrupted192_raw_arrays_exact']==12 and profile['probe_vs_formal_same_photo_exact'] is True
assert inp['native_source_photos_independently_decoded']==12 and inp['letterbox_conditions']==36 and inp['saved_arrays_verified']==108
assert inp['native_cv2_letterbox_exact_conditions']==36 and inp['resize_first_different_conditions']==12 and inp['resize_first_maximum_uint8_difference']==1
assert inp['resize_first_total_different_uint8_channels']==61051
assert sum(v['samples'] for v in inp['timing'].values())==324
assert jpeg['actual_processed_raw_arrays']==122 and jpeg['skipped_slots']==178 and jpeg['actual_image_forwards_with6warmups']==128
assert bank['actual_processed_raw_arrays']==187 and bank['skipped_slots']==113 and bank['actual_image_forwards_with6warmups']==193
assert jpeg['offered_slots']==bank['offered_slots']==300
assert bank['same_pixel_prior_raw_comparison_rows']==182 and bank['same_pixel_prior_unique_model_query_conditions']==31 and bank['framebank_input_images_verified']==12
assert 103+128+193==424 and 97+122+187==406
assert [c['processed'] for c in jpeg['cases']]==[60,45,17] and [c['processed'] for c in bank['cases']]==[98,69,20]
assert [c['deadline_misses'] for c in bank['cases']]==[16,69,20] and [c['skipped'] for c in bank['cases']]==[2,31,80]
assert bank['cases'][0]['observed_processed_fps']==4.9 and bank['cases'][0]['on_time']==82
assert bank['cases'][0]['frontend']['above200ms']==1
formal=[c for c in profile['profiles'] if not c['probe_only']]
assert [round(c['detector']['mean_ms'],2) for c in formal]==[158.79,261.82,1056.39]
assert [round(c['detector']['p95_ms'],2) for c in formal]==[161.19,263.47,1122.08]
assert all(c['cow_present_photos']==0 for c in formal) and [c['engine'] for c in formal]==['O8resident','O8resident','O6legacy']
assert board['status']=='ALL7_OWN_BOARD_PROCESSES_TERMINAL_AND_ABSENT_SSH_READ_CONFIRMED' and len(board['processes'])==7
assert all(not r['proc_exists'] for r in board['processes']) and board['services']=='active\nactive\n'
assert board['actual_IPs'].strip()=='192.168.2.99' and board['pynq_version']=='3.1.1' and board['machine']=='armv7l'
assert board['PL_after_bit_sha256']==profile['final_known_O8_bit_sha256']=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
assert board['PL_after_hwh_sha256']=='d6cf7f228c93f06523ad8e71efa9c280ba924ecc93d13f8ecdf90351238b4a6a'
for remote,local in [('protocol.json','protocol/board_v2.json'),('input_gate.json','protocol/input_gate_v1.json'),('stream_protocol.json','protocol/stream_v1.json'),
 ('framebank_protocol.json','protocol/framebank_v1.json'),('board_profile.py','tools/board_profile.py'),('board_input_probe.py','tools/board_input_probe.py'),
 ('board_stream_replay.py','tools/board_stream_replay.py'),('board_framebank_replay.py','tools/board_framebank_replay.py')]:assert board['task_runtime_hashes'][remote]==sha(ROOT/local)
for relative,transfer in [('profiles_complete.tar.gz','profiles_transfer.json'),('input_probe_complete.tar.gz','input_probe_transfer.json'),
 ('stream_replay_complete.tar.gz','stream_transfer.json'),('framebank_replay_complete.tar.gz','framebank_transfer.json')]:
    meta=load(ROOT/'evidence'/transfer);assert (ROOT/relative).stat().st_size==meta['bytes'] and sha(ROOT/relative)==meta['sha256']
archive=ROOT/'prior_interrupted_test.tar.gz';prior=load(ROOT/'delivery/recovery_record.json')
assert sha(archive)==prior['archive_sha256'] and archive.stat().st_size==prior['archive_bytes'] and prior['members']==39 and len(prior['empty_files'])==9
frozen=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'
assert sha(frozen)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
retained={frozen.relative_to(PROJECT).as_posix():sha(frozen)};accepted=load(frozen)
for key,hashkey in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
    file=Path(accepted[key]);assert sha(file)==accepted[hashkey];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
file=Path(accepted['source_event_record']['events_path']);assert sha(file)==accepted['source_event_record']['events_sha256'] and len(load(file))==12
retained[file.relative_to(PROJECT).as_posix()]=sha(file)
docs=[ROOT/'计划与验收.md',ROOT/'PYNQ实机三尺寸结果与下一步.md',ROOT/'Review与当前状态.md',PROJECT/'研究总览_从想法到论文.md',
      PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
links=[]
for doc in docs:
    text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
    for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',text):
        link=match.group(1) or match.group(2)
        if link.startswith(('http://','https://','#')):continue
        file=Path(unquote(link.split('#')[0]));file=file if file.is_absolute() else doc.parent/file
        assert file.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
recovery=load(PROJECT/'pynq_lowres_20261029/evidence/recovery_Jupyter01.json');assert recovery['own_kernel_removed'] is True
evidence=['protocol/board_v2.json','protocol/input_gate_v1.json','protocol/stream_v1.json','protocol/framebank_v1.json',
 'results/independent_profile_verification.json','results/independent_input_verification.json','results/independent_stream_verification.json',
 'results/independent_framebank_verification.json','results/final_board_state.json','results/all_profile_samples.csv','results/stream_samples.csv','results/framebank_samples.csv',
 'evidence/final_board_read01.json','evidence/collect_profiles01.json','evidence/collect_input_probe.json','evidence/collect_stream.json','evidence/collect_framebank.json',
 'evidence/periodic_verifier_diagnostic01.json','delivery/board_state_after_profiles.json','delivery/prior_interrupted_manifest.json',
 'stream_delivery/stream_replay/record.json','framebank_delivery/framebank_replay/record.json','input_delivery/input_probe/summary.json']
result={'status':'REAL_PYNQ_3SIZE_PROFILES_AND_TWO_PERIODIC_INPUT_CONTROLS_REVIEWED_WITH424_ACTUAL_FORWARDS',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'hardware_performance_phase_complete':True,'whole_goal_complete':False,
 'actual_PYNQ_FPGA_and_ARM_network_execution_verified':True,'PYNQ_version':board['pynq_version'],'actual_IP':board['actual_IPs'].strip(),'boot_id':board['boot_id'],
 'input_sizes':[192,256,320],'target_frontend_Hz':5,'formal_latency_means_ms':[c['detector']['mean_ms'] for c in formal],
 'formal_latency_P95_ms':[c['detector']['p95_ms'] for c in formal],'engines':['O8resident','O8resident','O6legacy'],'three_sizes_same_engine_control':False,
 'formal_samples':96,'probe_samples':1,'warmup_records':18,'total_actual_hardware_image_forwards':424,'raw_arrays_verified':406,
 'fixed_E010_raw_repeats_exact':60,'prior_interrupted192_raw_repeats_exact':12,'CPU_input_timing_operations':324,
 'independent_native_photo_decodes':12,'input_letterbox_conditions':36,'input_arrays_verified':108,
 'resize_before_rotation_different_conditions':12,'resize_before_rotation_maximum_uint8_delta':1,
 'jpeg_periodic_processed_3sizes':[60,45,17],'jpeg_periodic_skipped_3sizes':[40,55,83],
 'framebank_periodic_processed_3sizes':[98,69,20],'framebank_periodic_skipped_3sizes':[2,31,80],
 'framebank_deadline_misses_3sizes':[16,69,20],'framebank_observed_FPS_3sizes':[c['observed_processed_fps'] for c in bank['cases']],
 'same_pixel_raw_comparison_rows':182,'same_pixel_unique_model_query_conditions':31,
 'recovered_board_services_currently_accessible':True,'all7_own_board_processes_terminal_and_absent':True,'final_known_O8_bit_sha256':board['PL_after_bit_sha256'],
 'old_PID8082_result_admitted_for_performance':False,'old_interrupted39_files_preserved':True,'old_service_loss_root_cause_proven':False,
 'board_model_is_existing_COCO_quantized_assets':True,'current_cow_finetuned_weights_deployed':False,'cow_present_photos_each_fullinput_size':[0,0,0],
 'current12_cow_count_accuracy_admitted':False,'camera_hardware_active':False,'foreground_tracking_active':False,'background_identity_active':False,
 'complete_pipeline_stable5FPS_proven':False,'foreground_background_joint5FPS_proven':False,'new_training_updates':0,'new_independent_accuracy_test':False,
 'original_human12_milestone_preserved':True,'retained_artifact_hashes':retained,'evidence_hashes':{r:sha(ROOT/r) for r in evidence},
 'documents':[{'path':str(d.resolve()),'sha256':sha(d)} for d in docs],'local_links_checked':len(links),
 'manual_numeric_scope_and_causal_claim_review_completed':True,'new_scientific_figures_or_videos_generated_in_this_phase':0}
target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['retained_artifact_hashes','evidence_hashes','documents']}))
