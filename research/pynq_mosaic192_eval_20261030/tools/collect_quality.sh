set -euo pipefail
sacct -j 130635 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('pynq_mosaic192_eval_20261030');q=root/'results/quality'
state=subprocess.check_output(['sacct','-j','130635','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),state
s=json.loads((q/'summary.json').read_text());assert s['ORT_actual_forwards']=={'FP32':4225,'QDQ':4225} and s['native_integer_actual_forwards']==8
for row in json.loads((root/'results/artifact_manifest.json').read_text()):
 p=root/row['relative_file'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
files=[p for folder in ['results','protocol','logs','tools','input'] for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest=root/'quality_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2)+'\n')
a=root/'quality_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 for p in [*files,manifest]:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(a.resolve()),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files)+1,'manifest_files':len(files)}))
PY
