#!/usr/bin/env bash
#SBATCH --job-name=idcoo-source-labels
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/source-labels-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/source-labels-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
srun /share/home/renly/miniconda3/bin/python /share/home/renly/projects/idcoo_research_20261026/phase2/tools/source_timeline.py
