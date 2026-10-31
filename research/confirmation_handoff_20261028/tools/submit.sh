set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/confirmation_handoff_20261028
cd "$root"
test ! -e job_id.txt
test ! -e results/summary.json
mkdir -p results logs
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sha256sum protocol/handoff_v1.json tools/confirmation_counter.py input/zone_counter.py
jobid=$(sbatch --parsable tools/replay.slurm)
printf '%s\n' "$jobid" > job_id.txt
printf 'CONFIRMATION_HANDOFF_JOB_ID=%s\n' "$jobid"
