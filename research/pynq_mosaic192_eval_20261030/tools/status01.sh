set -euo pipefail
squeue -j 130635 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130635 -X --format=JobID,State,ExitCode,Elapsed -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
r=Path('/share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_eval_20261030')
f=r/'results/quality/summary.json'
if f.exists():
 s=json.loads(f.read_text());print(json.dumps({'status':s['status'],'forwards':s['ORT_actual_forwards'],'validation':s['validation_metrics'],'video':[dict(scene=x['scene'],mode=x['mode'],stride=x['stride'],down=x['down'],up=x['up'],TP_FP_FN=[x['formal_event_metrics'][k] for k in ['TP','FP','FN']] if x['formal_event_metrics'] else None) for x in s['video_metrics'] if x['counter']=='handoff_events']},indent=2))
else:print('\n'.join((r/'logs/quality-130635.out').read_text().splitlines()[-4:]))
print('STDERR_TAIL', (r/'logs/quality-130635.err').read_text()[-1800:])
PY
