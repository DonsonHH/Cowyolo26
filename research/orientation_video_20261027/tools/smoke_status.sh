set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_video_20261027
squeue -j 129934 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129934 --format=JobID,JobName%27,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$stage/logs/smoke-129934.out" || tail -n 3 "$stage/logs/smoke-129934.out" | cut -c 1-3400
test ! -s "$stage/logs/smoke-129934.err" || tail -n 18 "$stage/logs/smoke-129934.err"
test ! -f "$stage/results/smoke.json" || cat "$stage/results/smoke.json"
