set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/mosaic_pair_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
a=Path('evaluation_inputs_v1.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='3bf004be29533b0da2cfe80fef6736321dce2e4c7f09cbad6a67ecb6ee451bc7'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
print('EVALUATION_CONFIG_STAGED;NOT_SUBMITTED;ALL_SIX_COMPLETE_REQUIRED')
PY
