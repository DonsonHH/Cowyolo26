#!/usr/bin/env bash
#SBATCH --job-name=idcoo-diag-seam
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis/logs/capture-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis/logs/capture-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/phase3_diagnosis/tools/capture_raw_and_tracked.py
