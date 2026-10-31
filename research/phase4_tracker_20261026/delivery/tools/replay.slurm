#!/usr/bin/env bash
#SBATCH --job-name=idcoo-tracker-replay
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/phase4_tracker/logs/replay-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/phase4_tracker/logs/replay-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/phase4_tracker/tools/replay_tracker.py
