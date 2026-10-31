set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030
test ! -e figure_v2_job_id.txt
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
job_id=$(sbatch --parsable tools/plot_v2.slurm)
printf '%s\n' "$job_id" > figure_v2_job_id.txt
printf 'FIGURE_V2_JOB_ID=%s\n' "$job_id"
