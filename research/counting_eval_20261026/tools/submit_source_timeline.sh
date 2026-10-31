set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
mkdir -p "$ROOT/logs"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/source_timeline.slurm" | tee "$ROOT/logs/source_timeline_jobid.txt"
