set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028
squeue -j 130304 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130304 --format=JobID,JobName%22,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/admission_130304.out"; then tail -c 3000 "$ROOT/logs/admission_130304.out"; fi
if test -f "$ROOT/logs/admission_130304.err"; then tail -c 2000 "$ROOT/logs/admission_130304.err"; fi
