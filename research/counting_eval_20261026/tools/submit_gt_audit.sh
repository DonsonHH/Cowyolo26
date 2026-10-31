set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/author_gt_audit.slurm" | tee "$ROOT/logs/author_gt_jobid.txt"
