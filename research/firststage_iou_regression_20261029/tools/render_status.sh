set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/firststage_iou_regression_20261029
squeue -j 130352 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130352 --format=JobID,JobName%28,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/render_130352.out"; then tail -c 4000 "$ROOT/logs/render_130352.out"; fi
if test -f "$ROOT/logs/render_130352.err"; then tail -c 4000 "$ROOT/logs/render_130352.err"; fi
