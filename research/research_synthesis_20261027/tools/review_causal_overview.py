from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=ROOT/'results/overview_review_20261030_v7.json';j=json.loads(p.read_text(encoding='utf-8'))
assert j['new_model_forwards']==0 and j['new_board_mutations'] is True
j['new_model_forwards']=2441
j['new_model_forward_breakdown']={'actual_O8_timed':2309,'actual_O8_qualification':8,'actual_O8_warmup':12,'actual_ARM_identity_queries':39,'actual_ARM_identity_warmup':4,'CPU_Torch_queries':39,'CPU_Torch_gallery':30}
assert sum(j['new_model_forward_breakdown'].values())==2441
j['new_board_actions_performed']=j.pop('new_board_mutations')
b=PROJECT/'causal_photo_20261030/evidence/final_board_read.json';j['board_terminal_read']={'path':str(b.resolve()),'sha256':sha(b)}
j['corrections_before_freeze'].append('Final review replaced inherited prior-stage zero forward count and historical board-read binding with current2441 forward breakdown and current final board read. No experimental output changed.')
j['current_overview_review_completed_UTC']=datetime.now(timezone.utc).isoformat()
overview=Path(j['document']['path']);assert sha(overview)==j['document']['sha256']
for row in j['current_numeric_record_files']:assert sha(row['path'])==row['sha256']
text=overview.read_text(encoding='utf-8');assert '\ufffd' not in text and '10／10／10／10／9／9' in text and '最长身份完成80.89秒' in text
assert len(text.splitlines())>=200
j['entire_current_overview_read_in_full']=True;j['current_review_scope']='whole_existing_overview_plus_all_causal_photo_revisions;assistant_self_review_not_independent_human'
p.write_text(json.dumps(j,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'whole_overview_lines':len(text.splitlines()),'numeric_record_files_checked':len(j['current_numeric_record_files']),'current_new_forward_count':2441,'whole_goal_complete':False}))
