set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028
squeue -j 130005 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 130003,130004,130005 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/collect-130005.err" || cat "$root/logs/collect-130005.err"
if test "$(sacct -j 130005 -X -n -o State | xargs)" = COMPLETED; then cat "$root/results/delivery_record.json"; fi
