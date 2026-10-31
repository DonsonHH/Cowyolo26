#!/usr/bin/env bash
#SBATCH --job-name=cow-external-case
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028/logs/case-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028/logs/case-%j.err
set -euo pipefail
export OPENBLAS_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/render_case.py
