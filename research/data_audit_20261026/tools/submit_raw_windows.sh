set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/raw_windows.slurm" | tee "$ROOT/logs/raw_windows_jobid.txt"
