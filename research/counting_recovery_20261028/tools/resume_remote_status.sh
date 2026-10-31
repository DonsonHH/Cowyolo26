set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
cd "$root"
date -u
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
if test -f compact_v2_job_id.txt; then
  jobid=$(cat compact_v2_job_id.txt)
  sacct -j "$jobid" --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
  test ! -f "logs/compact-$jobid.err" || tail -n 20 "logs/compact-$jobid.err"
fi
test ! -f results/compact_delivery_record.json || cat results/compact_delivery_record.json
find results -maxdepth 1 -name '*compact*' -printf '%p %s bytes\n'
find media_runtime_wheels -maxdepth 1 -type f -printf '%p %s bytes\n' 2>/dev/null || true
