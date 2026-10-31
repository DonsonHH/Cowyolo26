set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_long_session_20261028
squeue -j 130319 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130319 --format=JobID,JobName%24,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS,AllocTRES%70
if test -f "$ROOT/logs/native_130319.out"; then tail -c 2600 "$ROOT/logs/native_130319.out"; fi
if test -f "$ROOT/logs/native_130319.err"; then tail -c 1600 "$ROOT/logs/native_130319.err"; fi
