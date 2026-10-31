set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/data_definition
job=$(cat "$ROOT/logs/audit_job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
sacct -j "$job" --format=JobID,State,ExitCode,Elapsed,MaxRSS,NodeList > "$ROOT/logs/slurm_final_status.txt"
test ! -e "$ROOT/delivery.tar.gz"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/collect.slurm" | tee "$ROOT/logs/collect_job_id.txt"
