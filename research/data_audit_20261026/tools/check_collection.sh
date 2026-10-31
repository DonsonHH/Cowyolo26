ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129665 --format=JobID,State,ExitCode,Elapsed -n
tail -n 4 "$ROOT/logs/collect-evidence-129665.out"
tail -n 6 "$ROOT/logs/collect-evidence-129665.err"
ls -lh "$ROOT/results/idcoo_audit_delivery.tar.gz"
