set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_long_session_20261028
squeue -j 130320 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130320 --format=JobID,JobName%24,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/decode_130320.out"; then tail -c 6000 "$ROOT/logs/decode_130320.out"; fi
if test -f "$ROOT/logs/decode_130320.err"; then tail -c 1200 "$ROOT/logs/decode_130320.err"; fi
