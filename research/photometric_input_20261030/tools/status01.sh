set -euo pipefail
squeue -j 130611 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130611 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/study-130611.out
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/study-130611.err
