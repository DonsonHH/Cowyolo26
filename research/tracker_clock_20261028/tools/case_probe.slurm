#!/usr/bin/env bash
#SBATCH --job-name=cow-clock-case-probe
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028/logs/probe-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028/logs/probe-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/case_probe.py
