set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/qat_study
sacct -j 129737 -X --format=JobID,JobName%24,State,ExitCode,Elapsed,NodeList
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
find "$ROOT" -maxdepth 3 -type f -printf '%s %p\n'
