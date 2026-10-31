#!/bin/bash
#SBATCH --job-name=cow-factorial-lane-crop
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/factorial_lane_crop_20261029/logs/crop-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/factorial_lane_crop_20261029/logs/crop-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/factorial_lane_crop_20261029
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
../env/bin/python tools/run_crop.py
