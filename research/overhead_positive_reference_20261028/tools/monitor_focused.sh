set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_positive_reference_20261028
sacct -j 130336 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/focused_130336.out"; then tail -c 2600 "$ROOT/logs/focused_130336.out"; fi
if test -f "$ROOT/logs/focused_130336.err"; then tail -c 1600 "$ROOT/logs/focused_130336.err"; fi
