set -u
ROOT=/share/home/renly/projects/idcoo_research_20261026/overhead_positive_reference_20261028
sacct -j 130333 --format=JobID,JobName%27,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS
if test -f "$ROOT/logs/admission_130333.out"; then tail -c 9500 "$ROOT/logs/admission_130333.out"; fi
if test -f "$ROOT/logs/admission_130333.err"; then tail -c 1800 "$ROOT/logs/admission_130333.err"; fi
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json
p=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_positive_reference_20261028')
rows=[]
for name in ['native_review_delivery.tar.gz','decode_diagnosis_delivery.tar.gz','results/native_review/summary.json','results/decode_diagnosis/summary.json']:
    f=p/name;rows.append({'file':name,'exists':f.exists(),'bytes':f.stat().st_size if f.exists() else None})
print(json.dumps({'artifacts':rows}))
PY
