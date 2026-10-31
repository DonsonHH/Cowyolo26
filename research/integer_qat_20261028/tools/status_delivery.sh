set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_qat_20261028
verify=$(cat "$root/verify_job_id.txt")
collect=$(cat "$root/collect_job_id.txt")
squeue -j "$collect" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j "129998,$verify,$collect" --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/collect-$collect.err" || cat "$root/logs/collect-$collect.err"
if test "$(sacct -j "$collect" -X -n -o State | xargs)" = COMPLETED; then cat "$root/results/delivery_record.json"; fi
