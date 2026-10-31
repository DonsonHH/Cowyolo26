#!/usr/bin/env bash
#SBATCH --job-name=idcoo-composition-collect
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/collect-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/composition_control/logs/collect-%j.err
set -euo pipefail
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/composition_control/tools/collect.py
