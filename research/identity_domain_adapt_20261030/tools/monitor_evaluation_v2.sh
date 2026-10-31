set -euo pipefail
squeue -j 130837 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j 130837 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
r=/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
for f in "$r/logs/evaluation-130837.out" "$r/logs/evaluation-130837.err"; do
 if test -f "$f"; then tail -n 10 "$f"; fi
done
