set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
test "$(sacct -j 129742 -X --format=State --noheader | tr -d ' ')" = FAILED
test ! -e "$ROOT/results/rounding_probe_training3.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --export=ALL,QAT_PROBE_INDEX=3 --parsable "$ROOT/tools/rounding.slurm" | tee "$ROOT/logs/activation_rounding_job_id.txt"
