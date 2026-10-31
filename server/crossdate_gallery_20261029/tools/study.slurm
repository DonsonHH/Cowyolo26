#!/bin/bash
#SBATCH --job-name=cow-crossdate-gallery
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029/logs/study-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029/logs/study-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029
export CUDA_VISIBLE_DEVICES=''
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
../env/bin/python tools/run_study.py
