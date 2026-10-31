set -euo pipefail
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,os,sys
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030');a=root/'payload.tar.gz'
assert hashlib.sha256(a.read_bytes()).hexdigest()=='c0c32ced76c65982b90806a0e1228557a36d5b4e291f9e76d0ab3d59083a51d9'
assert not (root/'launch.json').exists() and not (root/'results').exists()
with tarfile.open(a) as tar:
 assert len(tar.getmembers())==14
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='7c604db5d8330c69e4cf08f77fb2a317b3c63d748df2365a5073c3ff4792da6f'
protocol=json.loads((root/'protocol.json').read_text())
for row in protocol['payload_files']:
 f=root/row['file'];assert f.stat().st_size==row['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==row['sha256']
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_cow_vectors.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=os.environ.copy(),start_new_session=True)
r={'status':'REAL_MOSAIC192_O8_VECTOR_WORKER_STARTED','PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'size':192,'class_count':1,'primary_model':'mosaic050_seed26','expected_actual_model_forwards':10,'new_bitstream_programming':False}
with (root/'launch.json').open('x') as f:json.dump(r,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps(r))
PY
