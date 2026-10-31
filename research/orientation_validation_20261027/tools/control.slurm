#!/usr/bin/env bash
#SBATCH --job-name=idcoo-orientation-val
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:20:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027/logs/control-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027/logs/control-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export MKL_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export YOLO_AUTOINSTALL=false
export YOLO_OFFLINE=true
export WANDB_MODE=disabled
export COMET_MODE=DISABLED
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/orientation_validation_20261027/tools/run_orientation_control.py"
