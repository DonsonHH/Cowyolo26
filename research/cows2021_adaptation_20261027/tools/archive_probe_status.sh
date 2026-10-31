set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
ps -u renly -o pid,lstart,etime,time,state,args | awk '/[p]robe_archive_index.py/ {print}'
find "$stage/results/archive_index_probe" -maxdepth 1 -type f -printf '%f %s\n'
ps -p 2794954 -o pid,etime,state,args
test ! -f "$stage/results/download_attempt_01/progress.json" || cat "$stage/results/download_attempt_01/progress.json"
