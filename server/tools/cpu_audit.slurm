#!/usr/bin/env bash
#SBATCH --job-name=idcoo-data-audit
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/logs/cpu-audit-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/logs/cpu-audit-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONUNBUFFERED=1
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/tools/cpu_audit.py
