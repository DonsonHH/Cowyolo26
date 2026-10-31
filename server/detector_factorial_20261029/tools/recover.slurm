#!/bin/bash
#SBATCH --job-name=cow-factorial-freeze
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:04:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/recover-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/logs/recover-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
../env/bin/python tools/recover_completion.py
