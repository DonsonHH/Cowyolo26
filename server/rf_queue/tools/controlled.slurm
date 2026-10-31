#!/usr/bin/env bash
#SBATCH --job-name=idcoo-rf-queue
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/rf_queue/logs/controlled-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/rf_queue/logs/controlled-%j.err
set -euo pipefail
srun /share/home/renly/miniconda3/bin/python /share/home/renly/projects/idcoo_research_20261026/rf_queue/tools/test_association.py
srun /share/home/renly/miniconda3/bin/python /share/home/renly/projects/idcoo_research_20261026/rf_queue/tools/test_queue.py
srun /share/home/renly/miniconda3/bin/python /share/home/renly/projects/idcoo_research_20261026/rf_queue/tools/run_controlled.py
