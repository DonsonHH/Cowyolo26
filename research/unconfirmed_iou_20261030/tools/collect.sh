set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130637,130638,130639 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('unconfirmed_iou_20261030')
state=subprocess.check_output(['sacct','-j','130639','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),state
s=json.loads((root/'results/control_v2/summary.json').read_text());assert s['counter_paths']==444 and s['new_model_forwards']==0
for row in json.loads((root/'results/artifact_manifest_v2.json').read_text()):
 f=root/row['file'];assert f.stat().st_size==row['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256']
for row in json.loads((root/'protocol/failed_baselines_preserved.json').read_text()):assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
files=[f for folder in ['results','protocol','tools','logs'] for f in sorted((root/folder).rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
manifest=root/'transfer_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in files],indent=2)+'\n')
a=root/'control_delivery_v2.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(a.resolve()),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files)+1,'manifest_files':len(files)}))
rows=json.loads((root/'results/control_v2/paired_metrics.json').read_text())
primary=[r for r in rows if r['counter']=='handoff_events' and (r['cache'].startswith(('old_O8','new_O8','new_FP32','new_QDQ','native_')))]
changed=[r for r in rows if (r['baseline_down'],r['baseline_up'])!=(r['control_down'],r['control_up'])]
print(json.dumps({'primary':primary,'all_changed_scopes':len(changed),'changed_handoff':[r for r in changed if r['counter']=='handoff_events']},indent=2))
PY
