set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_training
audit=$(cat "$ROOT/logs/audit_job_id.txt")
study=$(cat "$ROOT/logs/study_job_id.txt")
reload=$(cat "$ROOT/logs/reload_job_id.txt")
for job in "$audit" "$study" "$reload"; do
  test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
done
sacct -j "$audit,$study,$reload" -P --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS | tee "$ROOT/results/final_slurm.txt"
test ! -e "$ROOT/training_delivery.tar.gz"
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/identity_training')
files=[]
for folder in ['tools','protocol','catalog','models','data','results','logs']:
    for p in sorted((root/folder).rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'delivery_manifest.json').write_text(json.dumps(files,indent=2))
PY
tar -czf "$ROOT/training_delivery.tar.gz" -C "$ROOT" tools protocol catalog models data results logs delivery_manifest.json
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/identity_training');bundle=root/'training_delivery.tar.gz'
record={'path':str(bundle),'bytes':bundle.stat().st_size,'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest()}
(root/'bundle_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
PY
