set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
test "$(sacct -j 129742 -X --format=State --noheader | tr -d ' ')" = FAILED
test ! -e "$ROOT/results/remaining_drift_probe.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/drift.slurm" | tee "$ROOT/logs/drift_job_id.txt"
PROJECT=/share/home/renly/projects/idcoo_research_20261026
for name in multicam_count_dev multicam_count_finetuned_dev; do
  find "$PROJECT/results/$name" -maxdepth 1 -type f -printf '%s %p\n'
  head -n3 "$PROJECT/results/$name/tracks.csv" || true
done
