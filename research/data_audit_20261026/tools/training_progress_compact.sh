ROOT=/share/home/renly/projects/idcoo_research_20261026
sacct -j 129663 --format=JobID,State,ExitCode,Elapsed -n
python - <<'PY'
from pathlib import Path
import csv,json
root=Path('/share/home/renly/projects/idcoo_research_20261026')
p=root/'results/detection_pilot/five_epoch_dev/results.csv'
if p.exists():
 rows=list(csv.DictReader(p.open()));print(json.dumps({'finished_epochs':len(rows),'last_metrics':rows[-1] if rows else None}))
record=root/'results/detection_pilot/training_record.json'
if record.exists():print(record.read_text())
else:
 p=root/'logs/det-pilot-129663.err'
 if p.exists():print(p.read_text()[-500:])
PY
