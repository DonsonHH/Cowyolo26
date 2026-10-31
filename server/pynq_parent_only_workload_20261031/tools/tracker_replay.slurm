#!/bin/bash
#SBATCH --job-name=cow-parent-track
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_workload_20261031/logs/tracker-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_workload_20261031/logs/tracker-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_workload_20261031
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/drop_counterfactual.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/plot_results.py
