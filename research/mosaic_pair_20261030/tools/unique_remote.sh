set -euo pipefail
test ! -e /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
test ! -e /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030_preflight_inputs_v1.tar.gz
sinfo -o "%P|%a|%D|%t|%N|%G"
squeue -u renly -o "%.18i|%.9P|%.28j|%.8T|%R"
