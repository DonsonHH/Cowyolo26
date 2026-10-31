#!/usr/bin/env bash
#SBATCH --job-name=idcoo-intref-opt
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/logs/optimizer-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/logs/optimizer-%j.err
set -euo pipefail
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/optimizer_probe.py
