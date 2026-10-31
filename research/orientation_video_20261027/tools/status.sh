set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_video_20261027
squeue -j 129940,129943 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129940,129943 --format=JobID,JobName%28,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$stage/logs/replay-129940.out" || tail -n 4 "$stage/logs/replay-129940.out" | cut -c 1-2800
test ! -s "$stage/logs/replay-129940.err" || tail -n 18 "$stage/logs/replay-129940.err"
test ! -s "$stage/logs/collect-129943.err" || tail -n 12 "$stage/logs/collect-129943.err"
if test -f "$stage/delivery_bundle.json"; then cat "$stage/delivery_bundle.json"; fi
