from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT.parent/'pynq_parent_only_workload_20261031/tools/verify_tracker_reference.py').read_text(encoding='utf-8')
changes=[
 ('ALL8_FULL_TRACKER','ALL4_FULL_TRACKER'),('tracker_job_id.txt','reference_job_id.txt'),
 ('logs/tracker_sacct.txt','logs/reference_sacct.txt'),('cow-parent-track','cow-parent-trigger'),
 ('logs/tracker-{job}.err','logs/verify-{job}.err'),
 ("assert plan['source_board_protocol_sha256'] == sha(BOARD / 'run_protocol.json')","assert load(REF / 'protocol/reference_v1.json')['source_board_protocol_sha256'] == sha(BOARD / 'run_protocol.json')"),
 ("assert len(reports) == len(summary['reports']) == 8","assert len(reports) == len(summary['reports']) == 4"),
 ("assert summary['counter_paths'] == 16","assert summary['counter_paths'] == 8"),
 ('ALL8_FULL_ASSOCIATIONS_AND16_EVENT_PATHS','ALL4_FULL_ASSOCIATIONS_AND8_EVENT_PATHS'),
 ("'counter_paths': 16","'counter_paths': 8")]
for before,after in changes:
 assert source.count(before)==1,(before,source.count(before));source=source.replace(before,after)
ast.parse(source)
with(ROOT/'tools/verify_tracker_reference.py').open('x',encoding='utf-8')as f:f.write(source)
print('Four-case tracker verifier prepared; no inference.')
