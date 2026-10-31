set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/long_video_fixed_replay_20261029
squeue -j 130345 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130345 --format=JobID,JobName%25,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS,AllocTRES%80
if test -f "$ROOT/logs/replay_130345.out"; then tail -c 5200 "$ROOT/logs/replay_130345.out"; fi
if test -f "$ROOT/logs/replay_130345.err"; then tail -c 1800 "$ROOT/logs/replay_130345.err"; fi
