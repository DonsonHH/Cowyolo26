#!/bin/bash
#SBATCH --job-name=cow-numpy-track-port
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_frontend_port_20261029/logs/regression-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_frontend_port_20261029/logs/regression-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_frontend_port_20261029
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
../env/bin/python -B regression.py
