from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
BASE=PROJECT/'identity_trigger_pair_20261030/tools'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records=[]
def derive(name,source,replacements=()):
 text=source.read_text(encoding='utf-8')
 for old,new,count in replacements:
  assert text.count(old)==count,(name,old,text.count(old));text=text.replace(old,new)
 if name.endswith('.py'):ast.parse(text)
 path=ROOT/'tools'/name
 with path.open('x',encoding='utf-8')as f:f.write(text)
 records.append({'source':str(source),'source_sha256':sha(source),'file':str(path),'sha256':sha(path)})
derive('verify_archive.py',PROJECT/'pynq_parent_only_workload_20261031/tools/verify_archive.py')
for name in['independent_geometry.py','verify_producer_records.py','verify_CPU_records.py']:
 derive(name,BASE/name)
derive('verify_board_results.py',BASE/'verify_board_results.py',[
 ("assert s['status']==t['status']", "assert sha(OUT/'run_protocol.json')==sha(ROOT/'protocol/run_v1.json')=='17e08b19b38d438351e005ecc6fa90256f65b7ec8f780aa517449d7c3856af4c'\nassert s['status']==t['status']",1),
 ("assert len(cases)==4 and rawchecks==s['actual_O8_forwards'] and ticks==4*1783+rawchecks and paths==8 and warmups==4",
  "assert len(cases)==4 and rawchecks==s['actual_O8_forwards'] and ticks==4*1783+rawchecks and paths==8 and warmups==4\nassert rawchecks<=p['maximum_timed_O8_forwards'] and jobs<=p['maximum_formal_identity_queries']\nassert rawchecks+16+jobs+warmups<=p['maximum_total_board_image_forwards']\nassert all(case['actual_background_jobs']<=p['maximum_identity_jobs_per_case']for case in cases)",1),
 ('FOUR_ACTUAL_COUNT_TRIGGER_MODEL_PAIR_RUNS_RAW_EVENTS_CAUSAL_PHOTOS_INPUTS_MODEL_MATCHED_SCORES_VERIFIED',
  'FOUR_PARENT_ONLY_ACTUAL_COUNT_TRIGGER_RUNS_RAW_EVENTS_CAUSAL_PHOTOS_INPUTS_AND_MODEL_MATCHED_SCORES_VERIFIED',1)])
for name in['launch_collection.sh','collection_status.sh']:
 derive(name,PROJECT/'pynq_parent_only_workload_20261031/tools'/name,[('cow_research_parent_only_workload_20261031','cow_research_parent_only_trigger_20261031',1)]if name=='collection_status.sh'else[
  ('cow_research_parent_only_workload_20261031','cow_research_parent_only_trigger_20261031',1),
  ('ALL8_WORKLOAD_2X2_MIRROR_ORDER_REPEATS_COMPLETE','ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE',1),
  ("root/'final_state.json'","root/'final_board_state.json'",1)])
derive('server_preflight.sh',PROJECT/'pynq_parent_only_workload_20261031/tools/server_preflight.sh')
with(ROOT/'evidence/verification_tools_preparation.json').open('x',encoding='utf-8')as f:json.dump({'created_UTC':datetime.now(timezone.utc).isoformat(),'records':records,'new_model_forwards':0},f,indent=2);f.write('\n')
print(json.dumps({'verification_tools_prepared':len(records),'new_model_forwards':0}))
