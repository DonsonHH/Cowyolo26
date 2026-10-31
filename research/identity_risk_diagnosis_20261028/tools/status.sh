set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/identity_risk_diagnosis_20261028
squeue -j 130002 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 130002 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/render-130002.err" || cat "$root/logs/render-130002.err"
if test "$(sacct -j 130002 -X -n -o State | xargs)" = COMPLETED; then cat "$root/results/delivery_record.json"; fi
