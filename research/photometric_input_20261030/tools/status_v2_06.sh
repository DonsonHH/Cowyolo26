set -euo pipefail
squeue -j 130613,130614,130615 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130613,130614,130615 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
r=Path('/share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030')
p=r/'results/study_v2/summary.json'
if p.exists():
 s=json.loads(p.read_text());print(json.dumps({'status':s['status'],'forwards':s['actual_total_forwards'],'validation':s['validation_metrics'],'video':[dict(condition=x['condition'],mode=x['mode'],scene=x['scene'],stride=x['stride'],down=x['down'],up=x['up'],TP_FP_FN=[x['formal_event_metrics'][k] for k in ['TP','FP','FN']] if x['formal_event_metrics'] else None) for x in s['video_metrics'] if x['counter']=='handoff_events']},indent=2))
else:
 print('SUMMARY_NOT_YET_WRITTEN')
 print('\n'.join((r/'logs/study-v2-130613.out').read_text().splitlines()[-3:]))
for job,name in [('130614','source-check'),('130615','media')]:
 for suffix in ['out','err']:
  f=r/'logs'/(name+'-'+job+'.'+suffix)
  if f.exists():print(f.name+':'+f.read_text()[-1500:])
PY
