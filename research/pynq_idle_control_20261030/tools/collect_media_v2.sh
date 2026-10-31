set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130588 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
root=Path('pynq_idle_control_20261030').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['sacct','-j','130588','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
q=root/'results/media';s=json.loads((q/'summary.json').read_text());assert s['photo_panels']==11
files=[p for p in q.iterdir() if p.is_file()]+[root/f for f in ['tools/render_media.py','protocol/media_v1.json','logs/media-130588.out','logs/media-130588.err']]
archive=root.parent/'pynq_idle_control_20261030_media.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for f in files:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)}
(root.parent/'pynq_idle_control_20261030_media_transfer.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
PY
