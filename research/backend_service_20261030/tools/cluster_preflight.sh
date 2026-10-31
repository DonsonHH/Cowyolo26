set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
id -un
hostname
pwd
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
scontrol show partition -o
df -hT /share/home/renly
test -x /share/home/renly/projects/idcoo_research_20261026/env/bin/python
test -f /share/home/renly/projects/idcoo_research_20261026/identity_training/results/study/C_letterbox_trained_seed26/best_encoder.pt
