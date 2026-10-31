set -euo pipefail
sacct -j 130620 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 4 /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/recover-130620.out
tail -n 6 /share/home/renly/projects/idcoo_research_20261026/training_coverage_20261030/logs/recover-130620.err
