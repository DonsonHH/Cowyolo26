set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib,json
root=Path('pynq_rot192_eval_20261029').resolve();a=root.parent/'pynq_rot192_eval_20261029_media_inputs.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()=='636d5356d1dcca2d87a9293f214840e856553f9e06bb5c8415f5331131b0389e'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
p=json.loads((root/'protocol/media_v1.json').read_text());a=root.parent/'pynq_rot192_eval_20261029_board_results.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()==p['board_archive_sha256'] and a.stat().st_size==p['board_archive_bytes']
out=root/'board_delivery';out.mkdir(exist_ok=False)
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==p['board_members']
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  file=(out/m.name).resolve();assert file.is_relative_to(out.resolve()) and not file.exists()
  file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(m).read())
for row in json.loads((out/'board_result_manifest.json').read_text()):assert hashlib.sha256((out/row['file']).read_bytes()).hexdigest()==row['sha256']
print('ACTUAL_BOARD_RAW_AND_EVENT_ARCHIVE_STAGED_WITHOUT_NEW_MODEL_FORWARDS')
PY
sbatch --parsable pynq_rot192_eval_20261029/tools/media.slurm
