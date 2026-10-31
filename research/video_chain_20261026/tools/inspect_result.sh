set -euo pipefail
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import json
r=Path('/share/home/renly/projects/idcoo_research_20261026/video_chain/results/replay')
s=json.loads((r/'summary.json').read_text());print(json.dumps({k:v for k,v in s.items() if k not in ['worker_messages','worker_ready']},indent=2))
print(json.dumps({'ready':s['worker_ready'],'worker_stop':[m for m in s['worker_messages'] if m['kind']=='stopped']},indent=2))
for event in json.loads((r/'events.json').read_text()):
    result=event.get('worker_result',{})
    print(json.dumps({'event':event['event_id'],'time_s':event['source_time_s'],'snapshot_frame':event.get('selected_snapshot',{}).get('source_frame'),
        'crop_size':event.get('selected_snapshot',{}).get('crop_size'),'status':event['status'],
        'conditions':[{'name':c['condition'],'candidate':c['candidate_anonymous_id'],'score':c['cosine_similarity'],'passes':c['passes_frozen_threshold']} for c in result.get('conditions',[])]}),flush=True)
PY
