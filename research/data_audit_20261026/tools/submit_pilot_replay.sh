set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129663 --format=JobID,State,ExitCode,Elapsed -n
test "$(sacct -j 129663 -X --format=State --noheader | tr -d ' ')" = COMPLETED
test -s "$ROOT/results/detection_pilot/training_record.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/replay_finetuned.slurm" | tee "$ROOT/logs/pilot_replay_jobid.txt"
