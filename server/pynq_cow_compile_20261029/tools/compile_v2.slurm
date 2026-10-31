#!/bin/bash
#SBATCH --job-name=cow-O8-compile-gate
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:12:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/logs/compile-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/logs/compile-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export YOLO_AUTOINSTALL=false
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/dependencies:/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
../env/bin/python tools/compile_old_seed26.py
