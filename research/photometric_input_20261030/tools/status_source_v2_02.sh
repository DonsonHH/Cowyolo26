set -euo pipefail
squeue -j 130616 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130616 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 5 /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/source-check-v2-130616.out
tail -n 5 /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/source-check-v2-130616.err
