"""Extend the unused standard preparer before CPU execution, keeping it intact."""
from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'tools/prepare_tracker_replay.py').read_text(encoding='utf-8')
changes=[
 ('srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py\n',
  'srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py\nsrun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/drop_counterfactual.py\n'),
 ("[replay, script, ROOT / 'tools/plot_results.py']", "[replay, script, ROOT / 'tools/plot_results.py', ROOT / 'tools/drop_counterfactual.py']"),
 ("'IDs_and_events_exact_required': True, 'model_forwards': 0,", "'IDs_and_events_exact_required': True, 'model_forwards': 0,\n            'posthoc_dropped_frame_diagnosis': 'All eight single missing-frame backfills and one all-missing control; previously seen source, no device change or human event accuracy claim.',")]
for old,new in changes:
 assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
ast.parse(source)
with(ROOT/'tools/prepare_tracker_with_drops_generated_v1.py').open('x',encoding='utf-8')as stream:stream.write(source)
print('CPU raw-only exploratory backfill preparer generated; no model execution.')
