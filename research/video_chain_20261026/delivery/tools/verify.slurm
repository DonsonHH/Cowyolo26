#!/usr/bin/env bash
#SBATCH --job-name=idcoo-video-evidence
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/video_chain/logs/verify-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/video_chain/logs/verify-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/video_chain/tools/verify_actual_worker.py
