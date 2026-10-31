set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,tarfile,hashlib
root=Path('pynq_periodic_joint_20261030').resolve()
archive=root.parent/'pynq_periodic_joint_20261030_media_inputs.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='1d6b987e1a16ce6acf3db452c51e360b27719d56851f549eeef9a433c886aabb'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
archive=root.parent/'pynq_periodic_joint_20261030_board_results.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='b21cb605d5e6df7d5f93fb45fae4a38223c191e4332bf0133cdeaf164acc2dc5'
out=root/'board_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(out/m.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
for row in json.loads((out/'result_manifest.json').read_text()):assert hashlib.sha256((out/row['file']).read_bytes()).hexdigest()==row['sha256']
PY
sbatch --parsable pynq_periodic_joint_20261030/tools/media.slurm
