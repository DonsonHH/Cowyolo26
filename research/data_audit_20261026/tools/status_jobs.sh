sacct -j 129649,129650 --format=JobID,JobName%24,Partition,State,ExitCode,Elapsed,MaxRSS -n
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
tail -n 10 /share/home/renly/projects/idcoo_research_20261026/logs/gpu-probe-129650.out
tail -n 12 /share/home/renly/projects/idcoo_research_20261026/logs/gpu-probe-129650.err
