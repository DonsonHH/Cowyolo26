set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/detector_training
train=$(cat "$ROOT/logs/train_job_id.txt")
infer=$(cat "$ROOT/logs/infer_job_id.txt")
collect=$(cat "$ROOT/logs/collect_job_id.txt")
sacct -j "$train,$infer,$collect" --format=JobID,JobName%28,State,ExitCode,Elapsed,MaxRSS,NodeList
if test -f "$ROOT/results/training/summary.json"; then head -n 15 "$ROOT/results/training/summary.json";fi
if test -f "$ROOT/results/inference/summary.json"; then head -n 12 "$ROOT/results/inference/summary.json";fi
if test -f "$ROOT/delivery_bundle.json"; then cat "$ROOT/delivery_bundle.json";fi
