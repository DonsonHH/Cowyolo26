#!/bin/bash
#SBATCH --job-name=cow-same-O8-sizes
#SBATCH --partition=cu
#SBATCH --array=0-1%2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=12G
#SBATCH --time=00:12:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030/logs/compile-%A_%a.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030/logs/compile-%A_%a.err
set -euo pipefail
case "$SLURM_ARRAY_TASK_ID" in
 0) fixed_case=s256 ;;
 1) fixed_case=s320 ;;
 *) exit 91 ;;
esac
cd /share/home/renly/projects/idcoo_research_20261026/pynq_o8_sizes_20261030/"$fixed_case"
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export YOLO_AUTOINSTALL=false
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/dependencies:/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
../../env/bin/python -B tools/compile_fixed_size.py
