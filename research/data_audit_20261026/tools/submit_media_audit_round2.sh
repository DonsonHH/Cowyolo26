set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
jobid=$(sbatch --export=ALL,AUDIT_RUN_NAME=media_audit_round2 --parsable "$ROOT/tools/cpu_audit.slurm")
printf '%s\n' "$jobid" | tee "$ROOT/logs/media_audit_round2_jobid.txt"
