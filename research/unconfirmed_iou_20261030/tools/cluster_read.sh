set -euo pipefail
id -un
hostname
printf '%s\n' "$HOME"
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
scontrol show partition -o
test ! -e /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030
test ! -e /share/home/renly/projects/idcoo_research_20261026/unconfirmed_iou_20261030_control_inputs_v1.tar.gz
