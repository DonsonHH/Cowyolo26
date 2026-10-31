set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/cows2021_identity_eval_20261030
sacct -j 130743 --format=JobID,JobName%24,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P > logs/sacct-130743.txt
grep -q '130743|cow-cows21-id-fixed|COMPLETED|0:0|' logs/sacct-130743.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
r=Path.cwd();summary=json.loads((r/'results/evaluation/summary.json').read_text());assert summary['actual_model_image_forwards']==1080 and summary['actual_network_calls']==90 and summary['Slurm_job_id']=='130743'
files=sorted([p for d in ['results','protocol','logs'] for p in(r/d).rglob('*') if p.is_file()]+[r/'submission.json',r/'submitted_job_id.txt'])
manifest=[{'file':p.relative_to(r).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
m=r/'result_manifest.json';assert not m.exists();m.write_text(json.dumps(manifest,indent=2)+'\n');files.append(m)
a=r/'identity_delivery_130743.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 for p in files:tar.add(p,arcname=p.relative_to(r).as_posix(),recursive=False)
print(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(a),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files),'manifest_files':len(manifest),'job_completed0_0':True}))
PY
