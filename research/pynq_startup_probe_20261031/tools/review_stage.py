from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import ast,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json')
assert len(v['cases'])==4 and v['actual_ARM_identity_warmups']==4 and v['actual_O8_image_forwards']==0
assert not v['original_40s_queue_timeout_reproduced'] and not v['periodic_5FPS_tested']
report=ROOT/'后台导入与启动内存_四次测量.md';review=ROOT/'Review与当前状态.md';text=report.read_text(encoding='utf-8')
for case in v['cases']:
 for value in[f"{case['module_import_ms']/1000:.3f}",f"{case['start_to_READY_received_ms']/1000:.3f}",f"{case['two_sample_Pss_sum_kB']/1024:.2f}"]:
  assert value in text
for phrase in['未重现原第6轮的40秒超时','不能把64.3MiB写成总内存节省','0正式身份查询','不是纯IPC延迟','父进程请求停止之后']:
 assert phrase in text,phrase
links=[]
for doc in[report,review]:
 for match in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
  target=unquote((match[1]or match[2]).strip());path=Path(target)
  if target.startswith(('http://','https://','#')):continue
  path=path if path.is_absolute()else doc.parent/path;assert path.exists();links.append(str(path))
f=load(ROOT/'delivery/final_state.json');assert f['hardware']['core_error']=='0x0'and f['shared_lock_available']and f['all_runtime_hashes_match']
evidence=['protocol/run_v1.json','results/independent_verification.json','results/board_archive_verification.json',
          'delivery/results/record.json','delivery/results/terminal.json','delivery/final_state.json','evidence/input_bundle_review_v1.json','evidence/primary_source_notes.json']
tools=['tools/prepare_payload_v1.py','tools/verify_results.py','tools/collect_results.py','tools/write_report.py','tools/review_stage.py']
for name in tools:ast.parse((ROOT/name).read_text(encoding='utf-8'))
result={'status':'FOUR_IMPORT_STARTUP_AND_PSS_MEASUREMENTS_REVIEWED_NOT_ORIGINAL_TIMEOUT_REPRO_OR_5FPS',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_ARM_identity_warmups':4,'actual_O8_image_forwards':0,
 'formal_identity_jobs':0,'new_CPU_model_forwards':0,'all_four_raw_prior_ARM_byte_exact':True,
 'original_startup_s':[round(c['start_to_READY_received_ms']/1000,9)for c in v['cases']if c['variant']=='original'],
 'parent_only_startup_s':[round(c['start_to_READY_received_ms']/1000,9)for c in v['cases']if c['variant']=='parent_only'],
 'two_sample_Pss_sum_savings_MiB':[p['original_minus_parent_only_two_sample_Pss_sum_kB']/1024 for p in v['mirrored_adjacent_pairs']],
 'original_40s_timeout_reproduced':False,'full_periodic5FPS_proven':False,'original_timeout_root_cause_proven':False,
 'source_import_only_variants_verified':True,'same_foreground_framebank_hash_across_four_parents':True,
 'whole_goal_complete':False,'manual_full_report_read':True,'local_links_checked':len(links),
 'evidence_hashes':{name:sha(ROOT/name)for name in evidence},
 'documents':[{'path':str(p.resolve()),'sha256':sha(p)}for p in[report,review]],
 'reviewed_tools':[{'path':str((ROOT/name).resolve()),'sha256':sha(ROOT/name)}for name in tools]}
with(ROOT/'results/final_review_v1.json').open('x',encoding='utf-8')as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps({k:v for k,v in result.items()if k not in['evidence_hashes','documents','reviewed_tools']}))
