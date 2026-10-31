ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129660,129661,129662,129663 --format=JobID,JobName%22,State,ExitCode,Elapsed,MaxRSS -n
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
tail -n 15 "$ROOT/logs/det-pilot-129663.out"
tail -c 2200 "$ROOT/logs/det-pilot-129663.err"
