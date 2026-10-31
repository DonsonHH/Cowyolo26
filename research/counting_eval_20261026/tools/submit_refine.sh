set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/refine_labels.slurm" | tee "$ROOT/logs/refine_labels_jobid.txt"
