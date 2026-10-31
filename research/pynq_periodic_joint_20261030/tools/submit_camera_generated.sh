set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
root=Path('pynq_periodic_joint_20261030');archive=Path('pynq_periodic_joint_20261030_inputs.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='a8539191ee8db803fd37faeb73205371ffdf5eb07f2caca363aabe59acecb4ef' and not root.exists()
root.mkdir();(root/'logs').mkdir();(root/'results').mkdir()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  file=(root/m.name).resolve();assert file.is_relative_to(root.resolve()) and not file.exists()
  file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable pynq_periodic_joint_20261030/tools/camera.slurm
