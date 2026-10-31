set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
job=$(cat "$ROOT/logs/portability_job_id.txt")
test "$(sacct -j "$job" -X --format=State --noheader | tr -d ' ')" = COMPLETED
sacct -j "$job" -P --format=JobID,JobName,State,ExitCode,Elapsed
cat "$ROOT/results/portability_probe/summary.json"
sha256sum "$ROOT/results/portability_probe/summary.json" "$ROOT/results/portability_probe/exact_input_and_outputs.npz"
