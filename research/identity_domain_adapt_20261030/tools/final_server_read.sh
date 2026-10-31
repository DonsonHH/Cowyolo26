set -euo pipefail
sacct -j 130772,130777,130835,130837 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
squeue -j 130772,130777,130835,130837 -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
r=Path('/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030');summary=json.loads((r/'results/evaluation/summary.json').read_text())
p=json.loads((r/'protocol/run_v1.json').read_text());terminals=[json.loads((r/'results/training'/c['name']/'terminal.json').read_text())for c in p['conditions']]
assert all(t['status']=='ONE_DOMAIN_TRAINING_CONDITION_COMPLETE'for t in terminals)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'status':'ALL6_TRAINING_AND_V2_EVALUATION_TERMINAL_ARTIFACTS_PRESENT',
 'training_job':'130777','evaluation_job':summary['Slurm_job_id'],'formal_updates':sum(t['optimizer_updates']for t in terminals),
 'formal_training_image_forwards':sum(t['training_image_forwards']for t in terminals),'evaluation_image_forwards':summary['actual_evaluation_model_image_forwards'],
 'future20_ID_pixels_opened':False,'archive_bytes':(r/'domain_delivery_v1.tar.gz').stat().st_size,'archive_sha256':hashlib.sha256((r/'domain_delivery_v1.tar.gz').read_bytes()).hexdigest(),'new_model_forwards_by_read':0}))
PY
