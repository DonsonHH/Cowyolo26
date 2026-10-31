set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/long_video_track_gap_20261029
squeue -j 130349 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130347,130348,130349 --format=JobID,JobName%25,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/control_130349.out"; then cat "$ROOT/logs/control_130349.out"; fi
if test -f "$ROOT/logs/control_130349.err"; then tail -c 4000 "$ROOT/logs/control_130349.err"; fi
