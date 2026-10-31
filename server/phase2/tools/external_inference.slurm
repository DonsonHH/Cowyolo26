#!/usr/bin/env bash
#SBATCH --job-name=idcoo-count-external
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:V100S:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:15:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/external-infer-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/phase2/logs/external-infer-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export YOLO_OFFLINE=true
export YOLO_CONFIG_DIR=/share/home/renly/projects/idcoo_research_20261026/yolo_settings
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/phase2/tools/external_counting_inference.py
