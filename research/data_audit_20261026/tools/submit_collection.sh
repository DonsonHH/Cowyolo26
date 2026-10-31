set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129664 --format=JobID,State,ExitCode,Elapsed -n
test "$(sacct -j 129664 -X --format=State --noheader | tr -d ' ')" = COMPLETED
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sacct -j 129649,129650,129655,129657,129658,129659,129660,129661,129662,129663,129664,129665 --format=JobID,JobName%24,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P > "$ROOT/results/slurm_jobs_final.txt"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R' > "$ROOT/results/queue_final.txt"
sbatch --parsable "$ROOT/tools/collect_evidence.slurm" | tee "$ROOT/logs/collection_jobid.txt"
