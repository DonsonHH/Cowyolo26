set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly
cd /share/home/renly/projects/idcoo_research_20261026/causal_photo_20261030
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import tarfile,hashlib,json
root=Path.cwd();a=root/'reference_payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='1967f1d4bec1c1468016dd75cc0bc835c1481ab71ada4005467a01fc2394a602'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==84
 for m in tar.getmembers():
  name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
  f=root.joinpath(*name.parts).resolve();assert f.is_relative_to(root) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
p=json.loads((root/'protocol/reference_v1.json').read_text())
for r in p['input_files']:assert hashlib.sha256((root/r['file']).read_bytes()).hexdigest()==r['sha256']
(root/'logs').mkdir(exist_ok=False)
print(json.dumps({'status':'REFERENCE_INPUTS_STAGED_HASHES_VERIFIED','photos':p['query_count']}))
PY
sbatch --parsable tools/reference.slurm
