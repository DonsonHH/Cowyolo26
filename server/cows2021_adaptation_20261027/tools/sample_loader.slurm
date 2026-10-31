#!/usr/bin/env bash
#SBATCH --job-name=idcoo-cows21-loader64
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/loader64-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/loader64-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export MKL_NUM_THREADS=2
export YOLO_AUTOINSTALL=false
export YOLO_OFFLINE=true
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/cows2021_adaptation_20261027/tools/sample_loader_check.py"
