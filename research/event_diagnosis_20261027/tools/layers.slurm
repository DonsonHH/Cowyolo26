#!/usr/bin/env bash
#SBATCH --job-name=idcoo-new-count-layers
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis/logs/layers-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis/logs/layers-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MPLCONFIGDIR=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis/cache/mpl
PY=/share/home/renly/projects/idcoo_research_20261026/env/bin/python
srun "$PY" /share/home/renly/projects/idcoo_research_20261026/event_diagnosis/tools/diagnose_new_layers.py
srun "$PY" /share/home/renly/projects/idcoo_research_20261026/event_diagnosis/tools/additional_controls.py
