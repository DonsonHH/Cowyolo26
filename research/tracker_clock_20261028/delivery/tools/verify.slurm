#!/usr/bin/env bash
#SBATCH --job-name=cow-clock-verify
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028/logs/verify-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028/logs/verify-%j.err
set -euo pipefail
export OPENBLAS_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/verify_collect.py
