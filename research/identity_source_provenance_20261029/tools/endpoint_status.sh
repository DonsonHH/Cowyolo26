set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/identity_source_provenance_20261029
squeue -j 130415 -o '%.18i|%.9P|%.26j|%.8T|%.10M|%.10l|%R'
sacct -j 130415 --format=JobID,JobName%28,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/endpoint_130415.out"; then cat "$ROOT/logs/endpoint_130415.out"; fi
if test -f "$ROOT/logs/endpoint_130415.err"; then tail -c 3500 "$ROOT/logs/endpoint_130415.err"; fi
