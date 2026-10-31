set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/firststage_iou_regression_20261029
squeue -j 130351 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130351 --format=JobID,JobName%28,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/regression_130351.out"; then tail -c 8000 "$ROOT/logs/regression_130351.out"; fi
if test -f "$ROOT/logs/regression_130351.err"; then tail -c 4000 "$ROOT/logs/regression_130351.err"; fi
