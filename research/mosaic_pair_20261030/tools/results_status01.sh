set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130630,130631,130632 -X --format=JobID,State,ExitCode,Elapsed -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030')
p=root/'results/evaluation_v2/summary.json'
if p.exists():
 s=json.loads(p.read_text());print(json.dumps({'video':[dict(condition=r['condition'],scene=r['scene'],stride=r['stride'],down=r['down'],up=r['up'],TP_FP_FN=[r['formal_event_metrics'][k] for k in ['TP','FP','FN']] if r['formal_event_metrics'] else None) for r in s['video_metrics'] if r['counter']=='handoff_events']},indent=2))
f=root/'results/control_weight_reproduction.json'
if f.exists():
 s=json.loads(f.read_text());print(json.dumps({'all3_state_dicts_exact':s['all3_state_dicts_exact'],'rows':[{k:r[k] for k in ['seed','state_tensors','state_tensors_byte_value_exact','maximum_tensor_value_error']} for r in s['rows']]}))
for name in ['media-130631.out','media-130631.err','control-weights-130632.err']:
 f=root/'logs'/name
 if f.exists():print(name+':'+f.read_text()[-1500:])
PY
