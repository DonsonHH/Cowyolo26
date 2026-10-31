#!/usr/bin/env bash
#SBATCH --job-name=idcoo-frozen-new-ids
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis/logs/future-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis/logs/future-%j.err
set -euo pipefail
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/quant_diagnosis/tools/evaluate_frozen_holdout.py
