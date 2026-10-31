set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/video_chain
replay=$(cat "$ROOT/logs/job_id.txt")
verify=$(cat "$ROOT/logs/verify_job_id.txt")
for job in "$replay" "$verify"; do test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED; done
sacct -j "$replay,$verify" -P --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS | tee "$ROOT/results/final_slurm.txt"
test ! -e "$ROOT/video_chain_delivery.tar.gz"
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/video_chain');files=[]
for folder in ['tools','protocol','logs','results']:
    for path in sorted((root/folder).rglob('*')):
        if path.is_file():files.append({'path':str(path.relative_to(root)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(root/'delivery_manifest.json').write_text(json.dumps(files,indent=2))
PY
tar -czf "$ROOT/video_chain_delivery.tar.gz" -C "$ROOT" tools protocol logs results delivery_manifest.json
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/video_chain');bundle=root/'video_chain_delivery.tar.gz'
record={'path':str(bundle),'bytes':bundle.stat().st_size,'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest()}
(root/'bundle_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
PY
