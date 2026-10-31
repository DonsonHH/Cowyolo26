set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
cat "$ROOT/logs/train-129841_0.err"
tail -c12000 "$ROOT/logs/train-129841_0.out" | tr "\r" "\n" | tail -n12
wc -l "$ROOT/results/training/mixed_seed26/results.csv"
find "$ROOT/results/training/mixed_seed26" -maxdepth 1 -type f -printf "%f %s\n"
