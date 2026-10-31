#!/usr/bin/env bash
#SBATCH --job-name=idcoo-count-score
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/count-score-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/count-score-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
srun /share/home/renly/miniconda3/bin/python "$ROOT/tools/test_zone_counter.py"
srun /share/home/renly/miniconda3/bin/python "$ROOT/tools/test_event_metrics.py"
srun /share/home/renly/miniconda3/bin/python "$ROOT/tools/score_counting.py"
