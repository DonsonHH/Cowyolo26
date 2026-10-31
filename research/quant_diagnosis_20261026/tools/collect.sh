set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
activation=$(cat "$ROOT/logs/activation_job_id.txt")
mixed=$(cat "$ROOT/logs/mixed_job_id.txt")
future=$(cat "$ROOT/logs/future_job_id.txt")
for job in "$activation" "$mixed" "$future"; do test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED; done
sacct -j "$activation,$mixed,$future" -P --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS | tee "$ROOT/results/final_slurm.txt"
test ! -e "$ROOT/quant_diagnosis_delivery.tar.gz"
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis');selected=[]
for folder in ['tools','protocol','catalog','logs','holdout_data','results']:
    selected.extend(p for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts)
rows=[{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in selected]
(root/'delivery_manifest.json').write_text(json.dumps(rows,indent=2))
bundle=root/'quant_diagnosis_delivery.tar.gz'
with tarfile.open(bundle,'w:gz') as archive:
    for path in selected:archive.add(path,arcname=str(path.relative_to(root)))
    archive.add(root/'delivery_manifest.json',arcname='delivery_manifest.json')
record={'bytes':bundle.stat().st_size,'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'manifest_files':len(rows),'path':str(bundle)}
(root/'bundle_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
PY
