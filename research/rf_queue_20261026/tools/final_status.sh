set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/rf_queue
job=$(cat "$ROOT/logs/job_id.txt")
sacct -j "$job" -P --format=JobID,JobName,State,ExitCode,Elapsed
tail -n 8 "$ROOT/logs/controlled-$job.err"
sha256sum "$ROOT/tools/association.py" "$ROOT/tools/queue_simulator.py" "$ROOT/tools/run_controlled.py" "$ROOT/protocol/controlled_rf_queue_v1.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
