#!/usr/bin/env bash
#SBATCH --job-name=idcoo-detector-collect
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/collect-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/detector_training/logs/collect-%j.err
set -euo pipefail
# Slurm accounting is queried on mu01 by submit_collect.sh; compute-node
# sacct points to an unavailable localhost database on this cluster.
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python /share/home/renly/projects/idcoo_research_20261026/detector_training/tools/collect.py
