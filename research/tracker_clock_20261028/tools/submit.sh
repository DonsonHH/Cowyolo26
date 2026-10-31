set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028
cd "$root"
test ! -e job_id.txt
test ! -e results/summary.json
mkdir -p logs results
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sha256sum protocol/clock_v1.json tools/replay.py tools/replay.slurm
jobid=$(sbatch --parsable tools/replay.slurm)
printf '%s\n' "$jobid" > job_id.txt
printf 'TRACKER_CLOCK_JOB_ID=%s\n' "$jobid"
