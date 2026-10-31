set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis
ids=""
for stage in capture layers source; do
 job=$(cat "$ROOT/logs/${stage}_job_id.txt")
 test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
 ids="${ids:+$ids,}$job"
done
sacct -j "$ids" --format=JobID,State,ExitCode,Elapsed,MaxRSS,NodeList > "$ROOT/logs/slurm_final_status.txt"
test ! -e "$ROOT/delivery.tar.gz"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/collect.slurm" | tee "$ROOT/logs/collect_job_id.txt"
