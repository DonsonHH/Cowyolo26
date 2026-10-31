#!/usr/bin/env bash
#SBATCH --job-name=idcoo-user-source-preview
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:08:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/source_demo/logs/preview-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/source_demo/logs/preview-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/source_demo/tools/build_scoped_preview.py
