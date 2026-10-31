set -euo pipefail
squeue -j 130743 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j 130743 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
r=/share/home/renly/projects/idcoo_research_20261026/cows2021_identity_eval_20261030
for file in "$r/logs/evaluation-130743.out" "$r/logs/evaluation-130743.err"; do
    if test -f "$file"; then tail -n 9 "$file"; fi
done
