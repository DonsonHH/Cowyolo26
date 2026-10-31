set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
squeue -j 129903 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129903 --format=JobID,JobName%25,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
test ! -f "$stage/results/metadata_preflight.json" || cat "$stage/results/metadata_preflight.json"
test ! -f "$stage/logs/metadata-129903.out" || tail -n 4 "$stage/logs/metadata-129903.out"
test ! -s "$stage/logs/metadata-129903.err" || tail -n 12 "$stage/logs/metadata-129903.err"
ps -p 2794954 -o pid,lstart,etime,state,args
test ! -f "$stage/results/download_attempt_01/progress.json" || cat "$stage/results/download_attempt_01/progress.json"
