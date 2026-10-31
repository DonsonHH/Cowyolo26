set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028
cd "$root"
test ! -e probe_job_id.txt
test ! -e results/case_probe
test "$(sacct -j "$(cat job_id.txt)" -X -n -o State | xargs)" = COMPLETED
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/case_probe.slurm)
printf '%s\n' "$jobid" > probe_job_id.txt
printf 'CASE_PROBE_JOB_ID=%s\n' "$jobid"
