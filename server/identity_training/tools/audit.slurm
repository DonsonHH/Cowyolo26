#!/usr/bin/env bash
#SBATCH --job-name=idcoo-train-inputs
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_training/logs/audit-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_training/logs/audit-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/identity_training/tools/audit_inputs.py
