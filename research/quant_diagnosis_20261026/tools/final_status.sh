set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis
activation=$(cat "$ROOT/logs/activation_job_id.txt")
mixed=$(cat "$ROOT/logs/mixed_job_id.txt")
future=$(cat "$ROOT/logs/future_job_id.txt")
portability=$(cat "$ROOT/logs/portability_job_id.txt")
sacct -j "$activation,$mixed,$future,$portability" -P --format=JobID,JobName,State,ExitCode,Elapsed
sha256sum "$ROOT/tools/probe_activations.py" "$ROOT/tools/compare_mixed_precision.py" "$ROOT/tools/evaluate_frozen_holdout.py" "$ROOT/tools/portability_probe.py" "$ROOT/protocol/mixed_precision_v1.json" "$ROOT/protocol/future_comparison_frozen.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
