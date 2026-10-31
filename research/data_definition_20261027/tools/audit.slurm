#!/usr/bin/env bash
#SBATCH --job-name=idcoo-box-definition-audit
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/data_definition/logs/audit-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/data_definition/logs/audit-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/data_definition/tools/audit_definitions.py
