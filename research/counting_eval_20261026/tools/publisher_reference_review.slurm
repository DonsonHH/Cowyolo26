#!/usr/bin/env bash
#SBATCH --job-name=idcoo-ref-review
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/ref-review-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/ref-review-%j.err
set -euo pipefail
export OPENBLAS_NUM_THREADS=2
srun /share/home/renly/miniconda3/bin/python /share/home/renly/projects/idcoo_research_20261026/phase2/tools/publisher_reference_review.py
