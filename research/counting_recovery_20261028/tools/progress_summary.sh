set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
jobid=$(cat "$root/retry_job_id.txt")
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/results/replay_v2')
for path in sorted(root.glob('*/summary.json')):
    d=json.loads(path.read_text());print(json.dumps({k:d[k] for k in ['name','predicted_down','predicted_up','raw_ROI_frames','tracked_ROI_frames','ROI_track_IDs','sampled_frames_in_scope','dense3sample_diagnostic_events']}))
PY
test ! -f "$root/logs/replay-$jobid.err" || tail -n 8 "$root/logs/replay-$jobid.err"
