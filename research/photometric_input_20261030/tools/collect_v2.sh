set -euo pipefail
sacct -j 130611,130612,130613,130614,130615,130616 --format=JobID,State,ExitCode,Elapsed,AllocCPUS,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('photometric_input_20261030')
for job in ['130613','130616','130615']:
 state=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
 assert state.startswith('COMPLETED|0:0'),(job,state)
summary=json.loads((root/'results/study_v2/summary.json').read_text())
assert summary['actual_total_forwards']==25350
verify=json.loads((root/'results/source_input_verification_v2.json').read_text())
assert verify['input_hashes_exact']==12675 and verify['anchor_pixel_arrays_exact']==30
media=json.loads((root/'results/media/media_values.json').read_text())
assert len(media['bars'])==30 and len(media['input_panels'])==30
for row in json.loads((root/'results/media/manifest.json').read_text()):
 file=root/'results/media'/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
manifest=json.loads((root/'results/artifact_manifest.json').read_text())
for row in manifest:
 file=root/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
failed=[]
for file in sorted((root/'results/study').rglob('*')):
 if file.is_file():failed.append({'file':file.relative_to(root).as_posix(),'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
assert len(failed)>0
failure_manifest=root/'results/failed_v1_artifact_manifest.json';assert not failure_manifest.exists()
failure_manifest.write_text(json.dumps(failed,indent=2)+'\n')
archive=root/'results_delivery_v2.tar.gz';assert not archive.exists()
files=[root/'results/artifact_manifest.json',root/'results/baseline_trace_probe.json',root/'results/source_input_verification_v2.json',failure_manifest,
 *sorted((root/'results/study_v2').rglob('*')),*sorted((root/'results/study').rglob('*')),*sorted((root/'results/media').glob('*')),*sorted((root/'logs').glob('*'))]
with tarfile.open(archive,'w:gz') as tar:
 for file in files:
  if file.is_file():tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(archive.resolve()),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len([p for p in files if p.is_file()]),'original_failed_results_included':True}))
PY
