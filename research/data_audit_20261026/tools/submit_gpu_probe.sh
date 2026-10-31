set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
test -s "$ROOT/models/yolo26n.pt"
jobid=$(sbatch --parsable "$ROOT/tools/gpu_probe.slurm")
printf '%s\n' "$jobid" | tee "$ROOT/logs/gpu_probe_jobid.txt"
