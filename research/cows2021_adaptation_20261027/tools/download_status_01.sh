set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
ps -p 2794954 -o pid,lstart,etime,state,args
test ! -f "$stage/results/download_attempt_01/progress.json" || cat "$stage/results/download_attempt_01/progress.json"
tail -n 3 "$stage/logs/download-attempt-01.log"
find "$stage/raw_images" -name '*.jpg' -printf '%f\n' | wc -l
find "$project/data" -maxdepth 2 -type f -name '*.zip' -printf '%s %p\n'
