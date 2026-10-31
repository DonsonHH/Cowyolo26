set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130581 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('pynq_periodic_joint_20261030').resolve();q=root/'results/camera_replay'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['sacct','-j','130581','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
s=json.loads((q/'summary.json').read_text());assert s['output_images']==392 and s['model_forwards']==0
for r in json.loads((q/'manifest.json').read_text()):assert sha(q/r['file'])==r['sha256']
files=[p for p in q.rglob('*') if p.is_file()]
archive=root.parent/'pynq_periodic_joint_20261030_camera.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files:tar.add(file,arcname=file.relative_to(q).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)}
(root.parent/'pynq_periodic_joint_20261030_camera_transfer.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));print(json.dumps(s))
PY
