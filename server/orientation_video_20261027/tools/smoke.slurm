#!/usr/bin/env bash
#SBATCH --job-name=idcoo-video-rot-smoke
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/orientation_video_20261027/logs/smoke-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/orientation_video_20261027/logs/smoke-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export YOLO_AUTOINSTALL=false
export YOLO_OFFLINE=true
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/orientation_video_20261027/tools/smoke.py"
