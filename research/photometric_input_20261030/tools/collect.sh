set -euo pipefail
sacct -j 130611 --format=JobID,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('photometric_input_20261030')
state=subprocess.check_output(['sacct','-j','130611','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
assert state.startswith('COMPLETED|0:0'),state
summary=json.loads((root/'results/study/summary.json').read_text())
assert summary['actual_total_forwards']==25350
manifest=json.loads((root/'results/artifact_manifest.json').read_text())
for row in manifest:
 file=root/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
archive=root/'results_delivery_v1.tar.gz';assert not archive.exists()
files=[root/'results/artifact_manifest.json',*sorted((root/'results/study').rglob('*')),*sorted((root/'logs').glob('*'))]
with tarfile.open(archive,'w:gz') as tar:
 for file in files:
  if file.is_file():tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(archive.resolve()),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len([p for p in files if p.is_file()])}))
PY
