set -euo pipefail
squeue -j 130613,130614,130615 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130613,130614,130615 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 3 /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/study-v2-130613.out
for file in /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/source-check-130614.out /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/source-check-130614.err /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/media-130615.out /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030/logs/media-130615.err; do if test -f "$file"; then tail -n 5 "$file"; fi; done
