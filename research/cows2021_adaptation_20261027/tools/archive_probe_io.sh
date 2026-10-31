set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
ps -p 3027396 -o pid,lstart,etime,time,pcpu,rss,state,args
if test -r /proc/3027396/io; then cat /proc/3027396/io; fi
find "$stage/results/archive_index_probe" -maxdepth 1 -type f -printf '%f %s\n'
