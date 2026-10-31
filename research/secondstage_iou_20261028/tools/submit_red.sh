set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028
cd "$root"
test ! -e red_job_id.txt
test ! -e results/baseline_red_tests.json
mkdir -p results logs
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable tools/baseline_test.slurm)
printf '%s\n' "$jobid" > red_job_id.txt
printf 'SECONDSTAGE_REAL_GATE_JOB_ID=%s\n' "$jobid"
