set -euo pipefail
squeue -j 130634 -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130634 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
tail -n 10 /share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_compile_20261030/logs/compile-130634.out
tail -n 8 /share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_compile_20261030/logs/compile-130634.err
