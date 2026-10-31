#!/usr/bin/env bash
#SBATCH --job-name=idcoo-new-event-seam
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis/logs/capture-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/event_diagnosis/logs/capture-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/event_diagnosis/tools/capture_new_raw.py
