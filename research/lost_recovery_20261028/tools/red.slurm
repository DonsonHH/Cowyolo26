#!/usr/bin/env bash
#SBATCH --job-name=cow-lost-red
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/lost_recovery_20261028/logs/red-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/lost_recovery_20261028/logs/red-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/lost_recovery_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/test_real_gate.py
