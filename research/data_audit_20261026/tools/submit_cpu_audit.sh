set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
test "$(stat -c%s "$ROOT/data/opencows2020/OpenCows2020.local-copy.zip.partial")" -eq 2272138852
jobid=$(sbatch --parsable "$ROOT/tools/cpu_audit.slurm")
printf '%s\n' "$jobid" | tee "$ROOT/logs/cpu_audit_jobid.txt"
