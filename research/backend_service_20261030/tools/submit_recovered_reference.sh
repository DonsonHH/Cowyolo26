set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly
cd /share/home/renly/projects/idcoo_research_20261026/backend_service_20261030
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import json,tarfile,hashlib
root=Path.cwd();a=root/'reference_payload_v1.tar.gz';assert hashlib.sha256(a.read_bytes()).hexdigest()=='d0637c5cdca424c922436e0c779d21124fd7a1fa36c684d80a194ea271de2427'
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==84
 for item in tar.getmembers():
  name=PurePosixPath(item.name);assert item.isfile() and not name.is_absolute() and '..' not in name.parts
  f=root.joinpath(*name.parts).resolve();assert f.is_relative_to(root) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(item).read())
p=json.loads((root/'protocol/reference_v1.json').read_text())
for row in p['input_files']:assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
assert b'\r\n' not in (root/'tools/reference.slurm').read_bytes()
(root/'logs').mkdir(exist_ok=False);print(json.dumps({'status':'RECOVERED_REFERENCE_INPUTS_HASH_VERIFIED','photos':p['query_count']}))
PY
sbatch --parsable tools/reference.slurm
