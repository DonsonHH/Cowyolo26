set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
r=Path('/share/home/renly/projects/idcoo_research_20261026')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[r/'phase3_diagnosis/results/capture/summary.json',r/'phase2/results/author_gt_audit/summary.json',r/'phase2/results/external_counting/all_summaries.json',r/'phase2/annotations/evaluation_protocol_v1.json']
for model in ['generic','pilot']:
    paths+=[r/f'phase3_diagnosis/results/capture/{model}/{name}' for name in ['raw_detector_boxes.csv','post_tracker_boxes.csv','tracks.csv','events.csv','summary.json']]
paths += [r/'models/yolo26n.pt',r/'results/detection_pilot/five_epoch_dev/weights/best.pt']
files=[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
print(json.dumps({'files':files,'author_reference':json.loads((r/'phase2/results/author_gt_audit/summary.json').read_text()),
                  'capture_summary':json.loads((r/'phase3_diagnosis/results/capture/summary.json').read_text())}))
PY
