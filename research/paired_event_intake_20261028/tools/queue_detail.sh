set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/paired_event_intake_20261028
jobid=$(cat "$root/exit_probe_job_id.txt")
date -u
squeue --start -j "$jobid"
scontrol show job "$jobid" -o
