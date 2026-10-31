set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/activation_range_20261028
squeue -j 130004 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 130003,130004 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/verify-130004.err" || tail -n 12 "$root/logs/verify-130004.err"
if test -f "$root/results/independent_verification.json"; then cat "$root/results/independent_verification.json"; fi
