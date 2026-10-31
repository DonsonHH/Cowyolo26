#!/usr/bin/env bash
#SBATCH --job-name=cow-count-recovery-check
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/verify-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/verify-%j.err
set -euo pipefail
export OPENBLAS_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/verify.py
