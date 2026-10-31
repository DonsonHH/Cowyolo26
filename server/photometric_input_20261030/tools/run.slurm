#!/bin/bash
#SBATCH --job-name=photometric-192
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:25:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/study-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/study-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/dependencies:/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
../env/bin/python -B tools/run_study.py
