#!/usr/bin/env bash
#SBATCH --job-name=idcoo-qat-cpu-drift
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/qat_study/logs/drift-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/qat_study/logs/drift-%j.err
set -euo pipefail
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/qat_study/tools/locate_remaining_drift.py
