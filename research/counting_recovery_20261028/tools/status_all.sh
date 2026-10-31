set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
main=$(cat "$root/retry_job_id.txt")
extra=$(cat "$root/full640_job_id.txt")
squeue -j "$main,$extra" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "$main,$extra" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/results')
for branch in ['replay_v2','full640_confirmation']:
    for path in sorted((root/branch).glob('*/summary.json')):
        d=json.loads(path.read_text());print(json.dumps({k:d[k] for k in ['name','predicted_down','predicted_up','raw_ROI_frames','tracked_ROI_frames','ROI_track_IDs','sampled_frames_in_scope','dense3sample_diagnostic_events']}))
PY
for job in "$main" "$extra"; do test ! -f "$root/logs/replay-$job.err" || tail -n 5 "$root/logs/replay-$job.err"; done
test ! -f "$root/logs/full640-$extra.err" || tail -n 5 "$root/logs/full640-$extra.err"
