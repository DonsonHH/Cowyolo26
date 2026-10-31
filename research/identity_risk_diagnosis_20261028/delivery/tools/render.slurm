#!/usr/bin/env bash
#SBATCH --job-name=idcoo-id-risk-fig
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/identity_risk_diagnosis_20261028/logs/render-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/identity_risk_diagnosis_20261028/logs/render-%j.err
set -euo pipefail
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MPLBACKEND=Agg
cd /share/home/renly/projects/idcoo_research_20261026/identity_risk_diagnosis_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/render.py
