set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028
squeue -j 130305 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130305 --format=JobID,JobName%22,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS,AllocTRES%80
if test -f "$ROOT/logs/inference_130305.out"; then tail -c 6500 "$ROOT/logs/inference_130305.out"; fi
if test -f "$ROOT/logs/inference_130305.err"; then tail -c 2200 "$ROOT/logs/inference_130305.err"; fi
