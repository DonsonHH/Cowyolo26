set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027
squeue -j 129932 -o '%.18i|%.9P|%.24j|%.8T|%R'
sacct -j 129932 --format=JobID,JobName%25,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$stage/results/figure_record.json" || cat "$stage/results/figure_record.json"
test ! -s "$stage/logs/figure-129932.err" || tail -n 12 "$stage/logs/figure-129932.err"
