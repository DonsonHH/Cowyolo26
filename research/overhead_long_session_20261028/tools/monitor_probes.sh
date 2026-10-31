set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_long_session_20261028
squeue -j 130326 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130326 --format=JobID,JobName%26,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/probes_130326.out"; then tail -c 2200 "$ROOT/logs/probes_130326.out"; fi
if test -f "$ROOT/logs/probes_130326.err"; then tail -c 1800 "$ROOT/logs/probes_130326.err"; fi
