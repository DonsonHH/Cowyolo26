set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/confirmed12_rf_stream_20261029
squeue -j 130363 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130363 --format=JobID,JobName%28,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/plots_130363.out"; then tail -c 2500 "$ROOT/logs/plots_130363.out"; fi
if test -f "$ROOT/logs/plots_130363.err"; then tail -c 3500 "$ROOT/logs/plots_130363.err"; fi
