set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
squeue -j 129983 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129981,129982,129983 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/optimizer-check-129983.err" || cat "$root/logs/optimizer-check-129983.err"
if test -f "$root/results/optimizer_independent_verification.json"; then
  cat "$root/results/optimizer_independent_verification.json"
fi
