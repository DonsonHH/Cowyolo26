set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
sacct -j 129675 --format=JobID,State,ExitCode,Elapsed -n
test "$(sacct -j 129675 -X --format=State --noheader | tr -d ' ')" = COMPLETED
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/score_counting.slurm" | tee "$ROOT/logs/scoring_jobid.txt"
