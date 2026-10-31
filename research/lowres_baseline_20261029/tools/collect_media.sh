set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
test "$(sacct -j 130504 --noheader --format=State -P | head -n1)" = COMPLETED
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029')
files=[f for f in sorted((root/'results/media').iterdir()) if f.is_file()]
files +=[root/'logs/media-130504.out',root/'logs/media-130504.err',root/'tools/render_media.py']
archive=root.parent/'lowres_baseline_20261029_media.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for f in files:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
record={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':len(files)}
p=root.parent/'lowres_baseline_20261029_media_transfer.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
