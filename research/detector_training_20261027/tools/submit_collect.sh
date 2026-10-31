set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
train=$(cat "$ROOT/logs/train_job_id.txt")
infer=$(cat "$ROOT/logs/infer_job_id.txt")
test "$(sacct -j "$train" -X --format=State --noheader | tr -d ' ')" = COMPLETED
test "$(sacct -j "$infer" -X --format=State --noheader | tr -d ' ')" = COMPLETED
reload=$(cat "$ROOT/logs/reload_job_id.txt")
test "$(sacct -j "$reload" -X --format=State --noheader | tr -d ' ')" = COMPLETED
sacct -j "$train,$infer,$reload,129797" --format=JobID,JobName%28,State,ExitCode,Elapsed,MaxRSS,NodeList > "$ROOT/logs/slurm_final_status.txt"
test ! -e "$ROOT/delivery.tar.gz"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/collect.slurm" | tee "$ROOT/logs/collect_job_id.txt"
