#!/usr/bin/env bash
#SBATCH --job-name=idcoo-orientation-fig
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027/logs/figure-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027/logs/figure-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/orientation_validation_20261027/tools/plot_results.py"
