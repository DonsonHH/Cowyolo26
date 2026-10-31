set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027
squeue -j 129929,129930 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129929,129930 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$stage/logs/control-129929.out" || tail -n 3 "$stage/logs/control-129929.out" | cut -c 1-2800
test ! -s "$stage/logs/control-129929.err" || tail -n 16 "$stage/logs/control-129929.err"
test ! -s "$stage/logs/collect-129930.err" || tail -n 12 "$stage/logs/collect-129930.err"
if test -f "$stage/delivery_bundle.json"; then cat "$stage/delivery_bundle.json"; fi
