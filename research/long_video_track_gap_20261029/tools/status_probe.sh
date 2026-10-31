set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/long_video_track_gap_20261029
squeue -j 130348 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130348 --format=JobID,JobName%25,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/probe_130348.out"; then cat "$ROOT/logs/probe_130348.out"; fi
if test -f "$ROOT/logs/probe_130348.err"; then tail -c 4000 "$ROOT/logs/probe_130348.err"; fi
