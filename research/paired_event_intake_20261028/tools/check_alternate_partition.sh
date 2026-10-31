set -euo pipefail
date -u
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
scontrol show partition 4gpu -o
scontrol show node gpu03 -o
scontrol show job "$(cat /share/home/renly/projects/idcoo_research_20261026/paired_event_intake_20261028/exit_probe_job_id.txt)" -o
