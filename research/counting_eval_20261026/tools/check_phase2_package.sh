ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
sacct -j 129688 --format=JobID,JobName%24,State,ExitCode,Elapsed -P
tail -n 4 "$ROOT/logs/eval-package-129688.out"
tail -n 6 "$ROOT/logs/eval-package-129688.err"
if test -s "$ROOT/results/bundle_record.json"; then cat "$ROOT/results/bundle_record.json"; fi
