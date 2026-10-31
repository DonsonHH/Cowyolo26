#!/usr/bin/env bash
#SBATCH --job-name=idcoo-collect-evidence
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/logs/collect-evidence-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/logs/collect-evidence-%j.err
set -euo pipefail
srun bash /share/home/renly/projects/idcoo_research_20261026/tools/collect_final_evidence.sh
