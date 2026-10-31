set -euo pipefail
id -un
hostname
printf '%s\n' "$HOME"
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
scontrol show partition -o
df -hT /share/home/renly
