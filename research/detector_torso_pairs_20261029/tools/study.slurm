#!/bin/bash
#SBATCH --job-name=cow-torso-pairs
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029/logs/pairs-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029/logs/pairs-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
../env/bin/python tools/run_pairs.py
