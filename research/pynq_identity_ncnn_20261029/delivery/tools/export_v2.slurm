#!/bin/bash
#SBATCH --job-name=body-ncnn-export
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/logs/export-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/logs/export-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/dependencies
../env/bin/python -B tools/export_encoder_v2.py
