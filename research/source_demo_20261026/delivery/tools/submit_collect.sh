set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
test "$(sacct -j 129746 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test "$(sacct -j 129744 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test "$(sacct -j 129742 -X --format=State --noheader | tr -d ' ')" = FAILED
test ! -e "$PROJECT/source_demo/delivery.tar.gz"
sacct -j 129737,129738,129740,129741,129742,129743,129744 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS > "$PROJECT/qat_study/logs/slurm_final_status.txt"
sacct -j 129746 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS > "$PROJECT/source_demo/logs/slurm_final_status.txt"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$PROJECT/source_demo/tools/collect.slurm" | tee "$PROJECT/source_demo/logs/collection_job_id.txt"
