set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase4_tracker
sacct -j 129694,129695 -P --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS | tee "$ROOT/results/final_slurm.txt"
test "$(sacct -j 129695 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/replay/summary.json"
test ! -e "$ROOT/results/tracker_delivery.tar.gz"
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/phase4_tracker')
files=[]
for folder in ['tools','protocol','logs','results/replay']:
    for p in sorted((root/folder).rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'results/delivery_manifest.json').write_text(json.dumps(files,indent=2))
PY
tar -czf "$ROOT/results/tracker_delivery.tar.gz" -C "$ROOT" tools protocol logs results/replay results/final_slurm.txt results/delivery_manifest.json
sha256sum "$ROOT/results/tracker_delivery.tar.gz"
wc -c "$ROOT/results/tracker_delivery.tar.gz"
