set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
for stage in train0 train freeze infer collect; do
 if test -f "$ROOT/logs/${stage}_job_id.txt"; then
  job=$(cat "$ROOT/logs/${stage}_job_id.txt")
  sacct -j "$job" -X --format=JobID,JobName%24,State,ExitCode,Elapsed
 fi
done
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/composition_control')
for path in sorted((root/'results/training').glob('*/progress.json')):
 print(json.dumps(json.loads(path.read_text())))
if (root/'results/all_models_frozen.json').exists():
 value=json.loads((root/'results/all_models_frozen.json').read_text())
 print(json.dumps({'freeze':value['status'],'paired_controls':value['paired_controls']}))
PY
if test -f "$ROOT/logs/infer_job_id.txt"; then
 job=$(cat "$ROOT/logs/infer_job_id.txt")
 if test -f "$ROOT/logs/infer-${job}.out"; then tail -n2 "$ROOT/logs/infer-${job}.out";fi
 if test -f "$ROOT/logs/infer-${job}.err"; then tail -n4 "$ROOT/logs/infer-${job}.err";fi
fi
if test -f "$ROOT/delivery_bundle.json"; then cat "$ROOT/delivery_bundle.json";fi
