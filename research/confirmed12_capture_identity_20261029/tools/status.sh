set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/confirmed12_capture_identity_20261029
squeue -j 130360 -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
sacct -j 130360 --format=JobID,JobName%28,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/replay_130360.out"; then tail -c 5000 "$ROOT/logs/replay_130360.out"; fi
if test -f "$ROOT/logs/replay_130360.err"; then tail -c 4000 "$ROOT/logs/replay_130360.err"; fi
