set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_positive_reference_20261028
squeue -j 130333 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130333 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/admission_130333.out"; then tail -c 4200 "$ROOT/logs/admission_130333.out"; fi
if test -f "$ROOT/logs/admission_130333.err"; then tail -c 1400 "$ROOT/logs/admission_130333.err"; fi
