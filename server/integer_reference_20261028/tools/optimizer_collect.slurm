#!/usr/bin/env bash
#SBATCH --job-name=idcoo-intref-opt-collect
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:03:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/logs/optimizer-collect-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028/logs/optimizer-collect-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/collect_optimizer.py
