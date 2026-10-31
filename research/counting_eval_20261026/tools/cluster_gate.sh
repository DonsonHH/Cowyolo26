set -e
id -un
hostname
printenv HOME
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
scontrol show partition -o
df -hT /share/home/renly
test -s /share/home/renly/projects/idcoo_research_20261026/results/detection_pilot/five_epoch_dev/weights/best.pt
find /share/home/renly/projects/idcoo_research_20261026/data/multicam_samples -name '*.mp4' -printf '%s %p\n'
