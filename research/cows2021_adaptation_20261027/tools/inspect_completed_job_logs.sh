set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,re
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
results=[]
for job,name in [(129918,'train'),(129919,'infer'),(129920,'collect')]:
    error=root/f'logs/{name}-{job}.err';output=root/f'logs/{name}-{job}.out'
    stderr=error.read_text(errors='replace') if error.exists() else ''
    stdout=output.read_text(errors='replace') if output.exists() else ''
    results.append({'job_id':job,'stderr_bytes':error.stat().st_size if error.exists() else None,
                    'stderr_tail':stderr[-3500:],
                    'unhandled_traceback_in_stderr':'Traceback (most recent call last)' in stderr,
                    'unhandled_traceback_in_stdout':'Traceback (most recent call last)' in stdout,
                    'output_tail':stdout[-1800:]})
print(json.dumps(results),flush=True)
PY
