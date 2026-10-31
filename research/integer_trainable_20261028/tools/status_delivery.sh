set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028
squeue -j 129993 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129989,129990,129991,129992,129993 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P
test ! -f "$root/logs/collect-129993.err" || tail -n 12 "$root/logs/collect-129993.err"
if test "$(sacct -j 129993 -X -n -o State | xargs)" = COMPLETED; then
  cat "$root/results/delivery_record.json"
  /share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
root=Path('/share/home/renly/projects/idcoo_research_20261026/integer_trainable_20261028/results')
d=json.loads((root/'export_graph_audit.json').read_text())
print(json.dumps({'newCPU_vs_prior_integer_reference':d['seed26_initial_CPU_vs_prior_integer_reference_max_difference'],
    'graphs':[{'seed':r['seed'],'phase':r['phase'],'QLinearAdd':r['actual_ALL_op_counts'].get('com.microsoft:QLinearAdd',0)} for r in d['new_export_graph_audits']]}))
PY
fi
