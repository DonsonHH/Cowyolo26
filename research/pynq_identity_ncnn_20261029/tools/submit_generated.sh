set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
getconf GNU_LIBC_VERSION
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,zipfile,os
root=Path('pynq_identity_ncnn_20261029');archive=Path('pynq_identity_ncnn_20261029_inputs.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='35de16504fc2064bdaf30f77dc755ff534204de27d217adfb15095dde42df71a'
assert not root.exists();root.mkdir();(root/'logs').mkdir();(root/'results').mkdir()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
sources=json.loads((root/'evidence/source_staging.json').read_text());deps=root/'dependencies';deps.mkdir()
for row in sources['artifacts']:
 p=root/'sources'/row['file'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 if p.suffix!='.whl':continue
 with zipfile.ZipFile(p) as z:
  for info in z.infolist():
   assert not info.filename.startswith('/') and '..' not in Path(info.filename).parts
   target=(deps/info.filename).resolve();assert target.is_relative_to(deps.resolve())
   if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
   assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(info))
   mode=(info.external_attr>>16)&0o777
   if mode:os.chmod(target,mode)
os.chmod(deps/'pnnx/pnnx',0o755)
print('PINNED_ENCODER132_INPUTS_AND_OFFLINE_NCNN_PNNX_DEPS_STAGED')
PY
sbatch --parsable pynq_identity_ncnn_20261029/tools/export.slurm
