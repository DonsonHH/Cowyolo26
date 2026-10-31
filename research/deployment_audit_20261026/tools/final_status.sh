set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
sacct -j 129717,129718,129719,129720 -P --format=JobID,JobName,State,ExitCode,Elapsed
if grep -q 'pthread_setaffinity_np failed' "$ROOT/logs/audit-129720.err"; then exit 91; fi
tail -n 10 "$ROOT/logs/audit-129720.err"
sha256sum "$ROOT/tools/export_and_quantise.py" "$ROOT/tools/bounded_quantisation.py" "$ROOT/tools/graph_audit.py" "$ROOT/protocol/export_ptq_v1.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
