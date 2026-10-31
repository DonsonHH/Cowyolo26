#!/bin/bash
#SBATCH --job-name=joint-periodic-media
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=3G
#SBATCH --time=00:08:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_idle_control_20261030/logs/media-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_idle_control_20261030/logs/media-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_idle_control_20261030
../env/bin/python -B tools/render_media.py
