set -euo pipefail
squeue -j 130734 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j 130734 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
task_dir=/share/home/renly/projects/idcoo_research_20261026/colo_eval_20261030
for file in "$task_dir/logs/evaluation-130734.out" "$task_dir/logs/evaluation-130734.err"; do
    if test -f "$file"; then tail -n 14 "$file"; fi
done
