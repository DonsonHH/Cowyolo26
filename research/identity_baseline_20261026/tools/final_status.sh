set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_baseline
sacct -j 129695,129696,129697,129698 -P --format=JobID,JobName,State,ExitCode,Elapsed
cat "$ROOT/logs/baseline-129697.err"
for pid in 1980899 1987769 2038308; do
  if test -e "/proc/$pid/cmdline"; then
    ps -p "$pid" -o pid=,stat=,etime=,args=
  else
    echo "Task staging PID $pid is no longer present"
  fi
done
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sha256sum "$ROOT/tools/run_identity_baseline.py" "$ROOT/tools/aggregate_identity.py" "$ROOT/protocol/identity_pilot_v1.json" "$ROOT/protocol/aggregation_v1.json"
