#!/bin/bash
#SBATCH --job-name=joint-native-camera-ROI
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=3G
#SBATCH --time=00:08:00
#SBATCH --output=/share/home/renly/projects/idcoo_research_20261026/pynq_periodic_joint_20261030/logs/camera-%j.out
#SBATCH --error=/share/home/renly/projects/idcoo_research_20261026/pynq_periodic_joint_20261030/logs/camera-%j.err
set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_periodic_joint_20261030
../env/bin/python -B tools/prepare_camera_replay.py
