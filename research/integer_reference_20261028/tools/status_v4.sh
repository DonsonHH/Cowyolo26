set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028
squeue -j 129978 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129975,129976,129977,129978 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
for file in "$root/logs/reference-129975.err" "$root/logs/reference-129976.err" "$root/logs/check-129977.err" "$root/logs/collect-129978.err"; do
  test ! -e "$file" || cat "$file"
done
if test "$(sacct -j 129978 -X -n -o State | xargs)" = COMPLETED; then
  cat "$root/results/delivery_record.json"
  sha256sum "$root/results/delivery.tar.gz"
fi
