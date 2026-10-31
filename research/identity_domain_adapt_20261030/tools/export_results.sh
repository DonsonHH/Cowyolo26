set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030
eval_id=$(cat evaluation_job_id.txt)
sacct -j "$eval_id" --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P > "logs/sacct-evaluation-${eval_id}.txt"
grep -q "${eval_id}|cow-id-domain-eval|COMPLETED|0:0|" "logs/sacct-evaluation-${eval_id}.txt"
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
r=Path.cwd();s=json.loads((r/'results/evaluation/summary.json').read_text());assert s['actual_evaluation_model_image_forwards']==3780 and len(s['outcomes'])==42
files=sorted([p for d in ['results','logs','protocol']for p in(r/d).rglob('*')if p.is_file()]+[r/'smoke_job_id.txt',r/'training_job_id.txt',r/'evaluation_job_id.txt'])
manifest=[{'file':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in files]
m=r/'result_manifest.json';assert not m.exists();m.write_text(json.dumps(manifest,indent=2)+'\n');files.append(m)
a=r/'domain_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for p in files:tar.add(p,arcname=p.relative_to(r).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(a),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files),'manifest_files':len(manifest),'all6_last_encoder_checkpoints_included':True}))
PY
