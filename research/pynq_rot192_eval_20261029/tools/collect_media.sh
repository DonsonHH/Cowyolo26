set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130575 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('pynq_rot192_eval_20261029').resolve();q=root/'results/media'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
state=subprocess.check_output(['sacct','-j','130575','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0')
files=[p for p in q.iterdir() if p.is_file()]+[root/r for r in ['protocol/media_v1.json','tools/render_media.py','tools/media.slurm','logs/media-130575.out','logs/media-130575.err']]
archive=root.parent/'pynq_rot192_eval_20261029_media.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
record={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)}
(root.parent/'pynq_rot192_eval_20261029_media_transfer.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
