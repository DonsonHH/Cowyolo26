from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
overview=PROJECT/'研究阶段总结_20261030.md';p=ROOT/'results/overview_review_20261030_v9.json';j=load(p)
assert sum(j['new_model_forward_breakdown'].values())==1595 and j['whole_goal_complete'] is False
for row in j['current_numeric_record_files']:assert sha(row['path'])==row['sha256']
updates=ROOT/'results/async_highres_entrypoint_updates_20261030.json';data=load(updates)
for row in data['updates']:
 if Path(row['path'])==overview:row['after_sha256']=sha(overview)
 else:assert sha(row['path'])==row['after_sha256']
updates.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
j['document']['sha256']=sha(overview);j['entrypoint_update_evidence']['sha256']=sha(updates)
old=next(Path(r['before_snapshot']) for r in data['updates'] if Path(r['path'])==overview).read_text(encoding='utf-8');text=overview.read_text(encoding='utf-8')
j['overview_changed_lines_manually_reviewed']=list(difflib.unified_diff(old.splitlines(),text.splitlines(),lineterm=''))
j['corrections_before_freeze'].append('Current whole overview read in full; historical microbench sentence explicitly scoped to its stage and performance heading changed to neutral throughput, deadlines and backend wait. No phase evidence changed.')
j['current_overview_review_completed_UTC']=datetime.now(timezone.utc).isoformat();j['entire_current_overview_read_in_full']=True
p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'overview_lines':len(text.splitlines()),'numeric_bindings_checked':len(j['current_numeric_record_files']),'whole_goal_complete':False}))
