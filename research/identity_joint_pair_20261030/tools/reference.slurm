#!/bin/bash
#SBATCH --job-name=cow-id-joint-ref
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030/logs/reference-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030/logs/reference-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/dependencies
cd /share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/cpu_reference.py
