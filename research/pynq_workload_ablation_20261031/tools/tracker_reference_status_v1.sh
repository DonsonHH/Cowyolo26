set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_workload_ablation_20261031
tracker_job_id=$(cat tracker_job_id.txt)
squeue -j "$tracker_job_id" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j "$tracker_job_id" --format=JobID,JobName%40,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
for name in ['results/tracker_replay/summary.json','results/figure_manifest.json']:
 path=Path(name)
 if path.exists():print(path.read_text(),flush=True)
PY
