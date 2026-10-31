#!/bin/bash
#SBATCH --job-name=cow-beca-score-plot
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=2G
#SBATCH --time=00:03:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031/logs/plot-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031/logs/plot-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR=/share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031/mplconfig
cd /share/home/renly/projects/idcoo_research_20261026/beca_score_diagnosis_20261031
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/plot_states.py
