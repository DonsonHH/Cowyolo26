#!/usr/bin/env bash
#SBATCH --job-name=cow-duplicate-audit-media
#SBATCH --partition=4gpu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/duplicate_track_audit_20261028/logs/render_v2-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/duplicate_track_audit_20261028/logs/render_v2-%j.err
set -euo pipefail
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2
cd /share/home/renly/projects/idcoo_research_20261026/duplicate_track_audit_20261028
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -u tools/render_v2.py
