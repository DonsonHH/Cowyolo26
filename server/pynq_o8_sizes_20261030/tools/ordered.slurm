#!/bin/bash
#SBATCH --job-name=O8-320-one-vector-probe
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=10G
#SBATCH --time=00:08:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030/logs/ordered-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030/logs/ordered-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
../env/bin/python -B tools/check_ordered_reference.py
