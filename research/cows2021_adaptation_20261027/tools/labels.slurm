#!/usr/bin/env bash
#SBATCH --job-name=idcoo-cows21-label-loader
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:20:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/labels-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/labels-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export MKL_NUM_THREADS=4
export YOLO_OFFLINE=true
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/cows2021_adaptation_20261027/tools/prepare_labels.py" --audit-attempt "$1" --output-tag "$2"
