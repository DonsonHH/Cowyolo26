#!/usr/bin/env bash
#SBATCH --job-name=idcoo-composition-data
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/prepare-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/prepare-%j.err
set -euo pipefail
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/composition_control/tools/prepare_data.py
