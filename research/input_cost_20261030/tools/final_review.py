from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,subprocess,sys,ast
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');s=load(ROOT/'delivery_v2/results/record.json');p=load(ROOT/'protocol/run_v2.json');failed=load(ROOT/'evidence/failed_run_record.json')
assert len(s['rows'])==256 and v['actual_O8_measured_forwards']==128 and v['actual_O8_qualification_forwards']==8 and v['actual_O8_warmups']==2
assert failed['rows']==[] and failed['actual_O8_forwards']==failed['actual_qualification_forwards']==failed['actual_warmups']==0
assert v['all16_raw_images_byte_equal_to_prior_full_O8'] and v['all128_case_raw_hashes_exact'] and v['parent_terminal_and_absent'] and v['known_O8_and_services_retained']
assert sha(ROOT/'tools/board_benchmark.py')==load(ROOT/'protocol/run_v1.json')['runner_sha256']
assert sha(ROOT/'tools/board_benchmark_v2.py')==p['runner_sha256']
cold=[r for r in v['groups'] if r['cache_request']=='cold_requested'];hot=[r for r in v['groups'] if r['cache_request']=='prewarmed']
assert len(cold)==len(hot)==4 and all(r['rows']==32 for r in cold+hot)
assert sum(r['before_nonresident_pages_total'] for r in cold)==20976 and all(r['after_nonresident_pages_total']==0 and r['positive_device_read_delta_cases']==32 for r in cold)
assert all(r['all_before_pages_resident']==32 and r['positive_device_read_delta_cases']==0 and r['device_read_sectors_total']==0 for r in hot)
red=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/check_target.py')],capture_output=True,text=True);assert red.returncode==1 and json.loads(red.stdout)['status']=='PERIODIC_TARGET_RED'
documents=[];links=0
for name in ['计划与验收.md','计量兼容修正_v2.md','高分输入取得成本与下一步.md','Review与当前状态.md']:
 f=ROOT/name;s=f.read_text(encoding='utf-8');assert '\ufffd' not in s
 for m in re.finditer(r'\]\(<([^>]+)>\)',s):assert Path(m[1]).exists();links+=1
 documents.append({'path':str(f.resolve()),'sha256':sha(f),'lines_read_and_reviewed':len(s.splitlines())})
for f in (ROOT/'tools').glob('*.py'):ast.parse(f.read_text(encoding='utf-8'))
names=['protocol/run_v1.json','protocol/run_v2.json','results/original_periodic_target_red.json','results/independent_verification.json',
 'evidence/failed_run_record.json','evidence/failed_record_get.json','evidence/board_preflight.json','evidence/accounting_probe.json','evidence/launch_v2.json','evidence/status_v2_01.json','evidence/collection_v2.json','evidence/archive_get_v2.json',
 'delivery_v2/results/record.json','delivery_v2/results/terminal.json','delivery_v2/final_state.json','tools/board_benchmark.py','tools/board_benchmark_v2.py','tools/verify_delivery.py','tools/check_target.py']
result={'status':'INPUT_COST256_READS138_REAL_O8_FORWARDS_FILE_RESIDENCY_DEVICE_STATS_AND_NONADOPTION_REVIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'source_images':16,'read_cases':256,'groups':8,'conditions_per_group':32,'actual_O8_measured_forwards':128,'actual_O8_qualification_forwards':8,'actual_O8_warmups':2,
 'failed_v1_read_cases':0,'failed_v1_all_model_forwards':0,'process_IO_counter_absent_preserved':True,'file_mincore_and_device_stats_verified':True,
 'cold_cases_with_nonresident_pages_and_positive_device_read_delta':128,'hot_cases_all_pages_resident_and_zero_device_read_delta':128,
 'all16_raws_byte_exact_to_prior_actual_same_model':True,'all128_raw_hashes_verified':True,'whole_device_bytes_claimed_process_bytes':False,
 'full_periodic_target_still_RED':True,'microbenchmark_is_full_pipeline_performance':False,'new_periodic_counter_or_identity_run':False,'new_policy_adopted':False,
 'immutable_copy_and_pickle_scope_disclosed':True,'global_cache_or_swap_changed':False,'parent_processes_terminal_absent':True,'original_O8_and_services_retained':True,
 'reviewer_kind':'assistant_self_review_and_separate_raw_output_hash_and_group_statistics_recomputation_not_independent_human','new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False,
 'documents':documents,'local_links_checked':links,'evidence_hashes':{name:sha(ROOT/name) for name in names}}
f=ROOT/'results/final_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:x for k,x in result.items() if k not in ['documents','evidence_hashes']}))
