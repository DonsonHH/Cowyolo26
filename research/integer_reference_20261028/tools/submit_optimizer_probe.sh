set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
cd "$root"
test ! -e optimizer_probe_job_id.txt
test ! -e results/optimizer_probe
sha256sum protocol/optimizer_probe_v1.json tools/optimizer_probe.py
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/optimizer_probe.slurm)
printf '%s\n' "$jobid" > optimizer_probe_job_id.txt
printf 'OPTIMIZER_PROBE_JOB_ID=%s\n' "$jobid"
