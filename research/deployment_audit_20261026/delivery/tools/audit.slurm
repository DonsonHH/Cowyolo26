#!/usr/bin/env bash
#SBATCH --job-name=idcoo-export-ptq-audit
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=12G
#SBATCH --time=00:20:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/logs/audit-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/logs/audit-%j.err
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/deployment_audit/dependencies_offline
export YOLO_AUTOINSTALL=false
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/deployment_audit/tools/test_graph_accounting.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/deployment_audit/tools/export_and_quantise.py
