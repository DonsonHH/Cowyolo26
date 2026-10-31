set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
squeue -j 129984 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129981,129982,129983,129984 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/optimizer-collect-129984.err" || cat "$root/logs/optimizer-collect-129984.err"
if test "$(sacct -j 129984 -X -n -o State | xargs)" = COMPLETED; then
  cat "$root/results/optimizer_delivery_record.json"
fi
