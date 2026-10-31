set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
squeue -j 129914,129915 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%R'
sacct -j 129914,129915 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
for job in image-audit-129914 archive-crc-129915; do
  test ! -f "$stage/logs/$job.out" || tail -n 4 "$stage/logs/$job.out"
  test ! -s "$stage/logs/$job.err" || tail -n 14 "$stage/logs/$job.err"
done
test ! -f "$stage/results/image_audit_01/summary.json" || cat "$stage/results/image_audit_01/summary.json"
