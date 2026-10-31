#!/usr/bin/env bash
#SBATCH --job-name=idcoo-cows21-collect
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/collect-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/collect-%j.err
set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/cows2021_adaptation_20261027/tools/collect.py"
