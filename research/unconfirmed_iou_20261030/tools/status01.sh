set -euo pipefail
squeue -j 130637 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130637 -X --format=JobID,State,ExitCode,Elapsed -P
tail -n 6 /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/control-130637.out
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/control-130637.err
