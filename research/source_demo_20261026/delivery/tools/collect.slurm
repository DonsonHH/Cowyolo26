#!/usr/bin/env bash
#SBATCH --job-name=idcoo-preview-qat-collect
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/results/preview-qat-collect-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/results/preview-qat-collect-%j.err
set -euo pipefail
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/source_demo/tools/collect_deliveries.py
