set -euo pipefail
stage=/share/home/renly/projects/idcoo_research_20261026/orientation_validation_20261027
sacct -j 129933 --format=JobID,JobName%27,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$stage/results/figure_record_v2.json" || cat "$stage/results/figure_record_v2.json"
test ! -s "$stage/logs/figure-v2-129933.err" || tail -n 12 "$stage/logs/figure-v2-129933.err"
