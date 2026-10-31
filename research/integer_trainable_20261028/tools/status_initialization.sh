set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
squeue -j 129994 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129994 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/initialization-129994.err" || cat "$root/logs/initialization-129994.err"
if test "$(sacct -j 129994 -X -n -o State | xargs)" = COMPLETED; then
  cat "$root/logs/initialization-129994.out"
  sha256sum "$root/results/initialization_probe.json"
fi
