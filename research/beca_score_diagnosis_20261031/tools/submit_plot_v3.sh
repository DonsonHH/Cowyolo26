set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031
test ! -e plot_v2_job_id.txt
squeue -u renly -o "%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R"
job_id=$(sbatch --parsable tools/plot_v3.slurm)
printf "%s\n" "$job_id" > plot_v2_job_id.txt
printf "BECA_SCORE_PLOT_V2_JOB_ID=%s\n" "$job_id"
