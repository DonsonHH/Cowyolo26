set -euo pipefail
sacct -j 130638 -X --format=JobID,State,ExitCode,Elapsed -P
tail -n 2 /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/baseline-probe-130638.out
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030/logs/baseline-probe-130638.err
