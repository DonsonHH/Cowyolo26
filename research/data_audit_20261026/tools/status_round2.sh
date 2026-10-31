set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129655,129657,129658,129659 --format=JobID,JobName%22,State,ExitCode,Elapsed,MaxRSS -n
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
tail -n 5 "$ROOT/logs/gpu-probe-129659.out"
tail -n 8 "$ROOT/logs/gpu-probe-129659.err"
tail -n 2 "$ROOT/logs/cpu-audit-129658.out"
