set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
job=$(cat "$ROOT/logs/job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/export_audit/summary.json"
if grep -q 'pthread_setaffinity_np failed' "$ROOT/logs/audit-$job.err"; then exit 91; fi
sacct -j "129719,$job" -P --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS | tee "$ROOT/results/final_slurm.txt"
test ! -e "$ROOT/export_delivery.tar.gz"
PYTHONPATH="$ROOT/dependencies_offline" /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/deployment_audit')
selected=[]
for folder in ['tools','protocol','logs','results/export_audit']:
    selected.extend(p for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts)
for file in ['results/final_slurm.txt','results/runtime_ready.json','results/export_audit_initial_129719/summary.json','export_wheels_record.json','wheelhouse/pypi_manifest.json']:
    selected.append(root/file)
rows=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in selected]
(root/'delivery_manifest.json').write_text(json.dumps(rows,indent=2))
bundle=root/'export_delivery.tar.gz'
with tarfile.open(bundle,'w:gz') as archive:
    for path in selected:archive.add(path,arcname=str(path.relative_to(root)))
    archive.add(root/'delivery_manifest.json',arcname='delivery_manifest.json')
record={'bytes':bundle.stat().st_size,'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'path':str(bundle),'manifest_files':len(rows)}
(root/'bundle_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
PY
