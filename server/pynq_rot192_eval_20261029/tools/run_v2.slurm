#!/bin/bash
#SBATCH --job-name=rot192-PTQ-quality
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:12:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_rot192_eval_20261029/logs/quality-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_rot192_eval_20261029/logs/quality-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_rot192_eval_20261029
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/dependencies:/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
../env/bin/python -B tools/evaluate_quality_v2.py
