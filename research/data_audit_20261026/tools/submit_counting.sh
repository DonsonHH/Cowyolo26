set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
test -s "$ROOT/results/gpu_probe.json"
jobid=$(sbatch --parsable "$ROOT/tools/counting_baseline.slurm")
printf '%s\n' "$jobid" | tee "$ROOT/logs/counting_dev_jobid.txt"
