#!/usr/bin/env bash
#SBATCH --job-name=idcoo-real-video-chain
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/video_chain/logs/replay-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/video_chain/logs/replay-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/video_chain/tools/test_snapshot_bank.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/video_chain/tools/run_video_chain.py
