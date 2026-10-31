set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
squeue -j 129914 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129914 --format=JobID,JobName%26,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
test ! -f "$stage/logs/image-audit-129914.out" || tail -n 5 "$stage/logs/image-audit-129914.out"
test ! -s "$stage/logs/image-audit-129914.err" || tail -n 14 "$stage/logs/image-audit-129914.err"
test ! -f "$stage/results/image_audit_01/summary.json" || cat "$stage/results/image_audit_01/summary.json"
