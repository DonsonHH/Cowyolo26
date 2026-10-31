set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/confirmed12_rf_stream_20261029
squeue -j 130362 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130362 --format=JobID,JobName%28,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/run_130362.out"; then tail -c 8500 "$ROOT/logs/run_130362.out"; fi
if test -f "$ROOT/logs/run_130362.err"; then tail -c 3500 "$ROOT/logs/run_130362.err"; fi
