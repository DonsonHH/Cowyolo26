set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
sacct -j 129696,129697,129698 -P --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS | tee "$ROOT/results/final_slurm.txt"
for job in 129696 129697 129698; do
  test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
done
test ! -e "$ROOT/identity_delivery.tar.gz"
/share/home/renly/miniconda3/bin/python - <<'PY'
from pathlib import Path
import hashlib,json
root=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline')
files=[]
for folder in ['tools','protocol','catalog','models','data','results','logs']:
    for p in sorted((root/folder).rglob('*')):
        if p.is_file():files.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(root/'delivery_manifest.json').write_text(json.dumps(files,indent=2))
PY
tar -czf "$ROOT/identity_delivery.tar.gz" -C "$ROOT" tools protocol catalog models data results logs delivery_manifest.json
sha256sum "$ROOT/identity_delivery.tar.gz"
wc -c "$ROOT/identity_delivery.tar.gz"
