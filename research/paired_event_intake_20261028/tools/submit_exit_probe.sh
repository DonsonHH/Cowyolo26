set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/paired_event_intake_20261028
cd "$root"
test ! -e exit_probe_job_id.txt
test ! -e results/exit_probe
mkdir -p logs results
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sha256sum protocol/exit_probe_v1.json tools/exit_probe.py tools/exit_probe.slurm
jobid=$(sbatch --parsable tools/exit_probe.slurm)
printf '%s\n' "$jobid" > exit_probe_job_id.txt
printf 'B_REGION_PROBE_JOB_ID=%s\n' "$jobid"
