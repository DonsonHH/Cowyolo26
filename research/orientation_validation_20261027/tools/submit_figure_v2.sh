set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027
test ! -e "$stage/figures_v2"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%R'
jobid=$(sbatch --parsable --job-name=idcoo-orientation-fig-v2 --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=2G --time=00:05:00 --output="$stage/logs/figure-v2-%j.out" --error="$stage/logs/figure-v2-%j.err" --wrap="srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python $stage/tools/plot_results_v2.py")
printf '%s\n' "$jobid" > "$stage/results/figure_v2_job_id.txt"
printf '%s\n' "$jobid"
