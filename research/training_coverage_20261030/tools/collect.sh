set -euo pipefail
sacct -j 130617,130618 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,json,hashlib,subprocess
root=Path('training_coverage_20261030')
for job in ['130617','130618']:
 state=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),state
for row in json.loads((root/'results/artifact_manifest.json').read_text()):
 p=root/row['file'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
a=root/'audit_delivery_v1.tar.gz';assert not a.exists()
files=[root/'results/artifact_manifest.json',*sorted((root/'results/audit').rglob('*')),*sorted((root/'results/media').rglob('*')),*sorted((root/'logs').glob('*'))]
with tarfile.open(a,'w:gz') as tar:
 for p in files:
  if p.is_file():tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(a.resolve()),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'files':len([p for p in files if p.is_file()])}))
PY
