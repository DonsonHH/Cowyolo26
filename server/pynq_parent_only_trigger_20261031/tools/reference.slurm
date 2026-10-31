#!/bin/bash
#SBATCH --job-name=cow-parent-trigger
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=5G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031/logs/verify-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031/logs/verify-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/reference_encoder.py
