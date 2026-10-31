set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
cd "$root"
test "$(sacct -j 130214 -X -n -o State | xargs)" = FAILED
test ! -e retry_job_id.txt
test ! -e results/replay_v2
/share/home/renly/projects/idcoo_research_20261026/env/bin/python -c 'from ultralytics.utils.checks import check_yaml; print(check_yaml("bytetrack.yaml"))'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/replay_v2.slurm)
printf '%s\n' "$jobid" > retry_job_id.txt
printf 'RECOVERY_RETRY_JOB_ID=%s\n' "$jobid"
