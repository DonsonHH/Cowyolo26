set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130567,130568 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('pynq_rot192_eval_20261029').resolve();q=root/'results/quality_v2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['sacct','-j','130568','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
s=json.loads((q/'summary.json').read_text());assert s['ORT_actual_forwards']=={'FP32':4225,'QDQ':4225} and s['native_integer_actual_forwards']==8
for row in json.loads((root/'results/artifact_manifest.json').read_text()):
 p=root/row['relative_file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
files=[p for folder in ['results','protocol','logs','tools','input'] for p in sorted((root/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest=root/'quality_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root.parent/'pynq_rot192_eval_20261029_quality.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in [*files,manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
(root.parent/'pynq_rot192_eval_20261029_quality_transfer.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r))
print(json.dumps({'video_metrics':[{'scene':r['scene'],'mode':r['mode'],'stride':r['stride'],'counter':r['counter'],'down':r['down'],'up':r['up'],
 'formal':[r['formal_event_metrics'][k] for k in ['TP','FP','FN']] if r['formal_event_metrics'] else None} for r in s['video_metrics']]}))
PY
