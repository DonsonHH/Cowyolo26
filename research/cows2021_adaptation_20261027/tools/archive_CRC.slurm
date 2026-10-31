#!/usr/bin/env bash
#SBATCH --job-name=idcoo-cows21-archive-crc
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/archive-crc-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/logs/archive-crc-%j.err
set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
srun "$project/env/bin/python" "$project/cows2021_adaptation_20261027/tools/verify_archive_image_CRC.py"
