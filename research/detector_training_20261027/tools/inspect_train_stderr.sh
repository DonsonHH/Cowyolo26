set -euo pipefail
P=/share/home/renly/projects/idcoo_research_20261026/detector_training
wc -c "$P/logs/train-129785.err"
tail -n 100 "$P/logs/train-129785.err"
find "$P/results/training" -maxdepth 1 -name "seed*_training_record.json" -printf "%f %s\n"
