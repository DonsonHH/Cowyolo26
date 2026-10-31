set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/paired_event_intake_20261028
jobid=$(cat "$root/exit_probe_job_id.txt")
test "$jobid" = 130276
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
test "$(squeue -h -j "$jobid" -o '%u')" = renly
test "$(squeue -h -j "$jobid" -o '%t')" = PD
test "$(squeue -h -j "$jobid" -o '%j')" = cow-B-region-probe
scontrol show job "$jobid" -o
scontrol update JobId="$jobid" Partition=4gpu
scontrol show job "$jobid" -o
printf 'SAME_JOB_CPU_ONLY_PARTITION_CHANGED=%s\n' "$jobid"
