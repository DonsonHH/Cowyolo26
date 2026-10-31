set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_final20_20261030
sacct -j 130877,130878,130879 --format=JobID,JobName,State,ExitCode,Elapsed,AllocCPUS,MaxRSS --parsable2
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib
r=Path.cwd();e=json.loads((r/'protocol/execution_v1.json').read_text());assert hashlib.sha256((r/'protocol/run_v1.json').read_bytes()).hexdigest()==e['protocol_sha256']
for path,digest in e['files_sha256'].items():assert hashlib.sha256((r/path).read_bytes()).hexdigest()==digest
for m in e['models']:assert hashlib.sha256(Path(m['checkpoint']).read_bytes()).hexdigest()==m['checkpoint_sha256']
s=json.loads((r/'results/evaluation/summary.json').read_text());assert s['actual_model_image_forwards']==180 and s['actual_network_calls']==16
print(json.dumps({'status':'FINAL20_ORIGINAL_EXECUTION_CODE_WEIGHTS_AND_RESULTS_UNCHANGED_AFTER_COLLECTION','model_image_forwards':180,'network_calls':16,'new_model_forwards_by_this_read':0}))
PY
