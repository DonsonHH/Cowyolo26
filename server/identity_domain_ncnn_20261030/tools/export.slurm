#!/bin/bash
#SBATCH --job-name=cow-new-id-ncnn
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030/logs/export-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030/logs/export-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/dependencies
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/convert_and_verify.py
