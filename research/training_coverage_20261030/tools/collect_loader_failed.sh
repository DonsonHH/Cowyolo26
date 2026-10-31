set -euo pipefail
sacct -j 130619,130620 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('training_coverage_20261030')
for job in ['130619','130620']:
 state=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('FAILED|1:0'),(job,state)
assert (root/'results/loader/objects.json').is_file() and (root/'results/loader/images.json').is_file() and (root/'results/loader/batches.json').is_file()
assert not (root/'results/loader/summary.json').exists()
files=[p for p in sorted((root/'results/loader').rglob('*')) if p.is_file()]
record=[{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
manifest=root/'results/failed_loader_artifact_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps(record,indent=2)+'\n')
a=root/'loader_failed_delivery_v1.tar.gz';assert not a.exists()
files += [manifest,*sorted((root/'logs').glob('loader-*')),*sorted((root/'logs').glob('recover-*'))]
with tarfile.open(a,'w:gz') as tar:
 for p in files:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(a.resolve()),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'files':len(files),'no_loader_rerun':True}))
print('RECOVERY_ERROR_LOG')
print((root/'logs/recover-130620.err').read_text())
PY
