set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027
test ! -e "$stage/results/source_archive_CRC_audit.json"
sinfo -o '%P|%a|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
jobid=$(sbatch --parsable "$stage/tools/archive_CRC.slurm")
printf '%s\n' "$jobid" > "$stage/results/archive_CRC_job_id.txt"
printf '%s\n' "$jobid"
squeue -j "$jobid" -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
