set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030');archive=root/'payload.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='e33f4d6c0bc2cd13a24b069203356f1c9f109ba0ce5852a294729de2a5209fc9'
assert not (root/'launch.json').exists() and not (root/'results').exists()
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==2666
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  path=(root/m.name).resolve();assert path.is_relative_to(root.resolve()) and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'board_protocol.json').read_bytes()).hexdigest()=='a570826ebdeedf2137da8413875e5e98fd90fb8c91be25409755213558e4c628'
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_video.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'actual_video_model_forwards_expected':2654,
 'warmups':2,'counter_paths_expected':6,'scope':'Unpaced PNG replay, actual O8 model and actual ARM counters; not livecamera or simultaneous identity.'}
(root/'launch.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
