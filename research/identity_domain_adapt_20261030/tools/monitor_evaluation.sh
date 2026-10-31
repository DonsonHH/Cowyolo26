set -euo pipefail
squeue -j 130835 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j 130835 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
r=/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
for f in "$r/logs/evaluation-130835.out" "$r/logs/evaluation-130835.err"; do
 if test -f "$f"; then tail -n 10 "$f"; fi
done
