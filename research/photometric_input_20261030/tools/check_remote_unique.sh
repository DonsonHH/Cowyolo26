set -euo pipefail
test ! -e /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030
test ! -e /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030_inputs_v1.tar.gz
squeue -u renly -o "%.18i|%.9P|%.28j|%.8T|%R"
