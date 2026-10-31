set -euo pipefail
sacct -j 130612 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cat /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/probe-130612.out
cat /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/probe-130612.err
