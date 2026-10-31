set -euo pipefail
squeue -j 130613,130614 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130613,130614 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 10 /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/study-v2-130613.out
tail -n 6 /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/study-v2-130613.err
