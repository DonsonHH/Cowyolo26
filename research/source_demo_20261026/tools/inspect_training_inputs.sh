set -euo pipefail
P=/share/home/renly/projects/idcoo_research_20261026
cat "$P/results/detection_pilot/five_epoch_dev/args.yaml"
cat "$P/data/opencows2020/derived_detection/summary.json"
cat "$P/data/opencows2020/derived_detection/data.yaml"
sinfo -o "%P|%a|%t|%N|%G"
squeue -u renly -o "%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R"
