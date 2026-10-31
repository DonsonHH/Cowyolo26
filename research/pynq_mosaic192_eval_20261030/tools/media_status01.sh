set -euo pipefail
squeue -j 130636 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130636 -X --format=JobID,State,ExitCode,Elapsed -P
tail -n 3 /share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_eval_20261030/logs/media-130636.out
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_eval_20261030/logs/media-130636.err
