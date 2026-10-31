set -euo pipefail
squeue -j 130621 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130621 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 4 /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/preflight-130621.out
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030/logs/preflight-130621.err
