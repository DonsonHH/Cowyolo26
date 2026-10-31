#!/usr/bin/env bash
#SBATCH --job-name=cow-count-recovery-collect
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/collect-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/logs/collect-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/collect.py
