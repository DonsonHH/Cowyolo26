set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
squeue -j 129907 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129907 --format=JobID,JobName%25,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
test ! -f "$stage/results/sample_loader_64/summary.json" || python - "$stage/results/sample_loader_64/summary.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print(json.dumps({k:v for k,v in r.items() if k!='records'}))
PY
test ! -f "$stage/logs/loader64-129907.out" || tail -n 4 "$stage/logs/loader64-129907.out"
test ! -s "$stage/logs/loader64-129907.err" || tail -n 12 "$stage/logs/loader64-129907.err"
