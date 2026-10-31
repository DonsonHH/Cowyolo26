set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/orientation_video_20261027"
sacct -j 129936 --format=JobID,JobName%27,State,ExitCode,Elapsed,MaxRSS -P
test ! -s "$stage/logs/box-smoke-129936.err" || tail -n 14 "$stage/logs/box-smoke-129936.err"
test ! -f "$stage/logs/box-smoke-129936.out" || tail -n 2 "$stage/logs/box-smoke-129936.out"
if test -f "$stage/results/nonempty_seam_smoke.json"; then
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json
p=Path('/share/home/renly/projects/idcoo_research_20261026/orientation_video_20261027/results/nonempty_seam_smoke.json')
r=json.loads(p.read_text());print(json.dumps({'status':r['status'],'records':[{'orientation':x['orientation'],'raw':len(x['pretracker_boxes']),'post':len(x['posttracker_data']),'native_HW':[x['native_H'],x['native_W']],'mapping_max_diff':max(s['max_float32_inverse_difference'] for s in x['seam_checks'])} for x in r['records']]}))
PY
fi
