set -euo pipefail
squeue -j 130619 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130619 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 6 /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/loader-130619.out
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/loader-130619.err
