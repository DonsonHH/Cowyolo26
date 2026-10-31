set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path, PurePosixPath
import ast,fcntl,hashlib,json,os,subprocess,tarfile
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031')
archive=root/'startup_input_v1.tar.gz'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert not(root/'launch.json').exists() and not(root/'results').exists()
assert archive.stat().st_size==14680 and sha(archive)=='c4f646cc0b28e50efd8cbad9954cefdc2181021a6a17ca419da45b755ab6c840'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==len({row.name for row in members})==9
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile() and len(rel.parts)==1 and not rel.is_absolute()
  path=root/row.name;assert not path.exists();path.write_bytes(tar.extractfile(row).read())
assert sha(root/'run_protocol.json')=='00098eb29e29c79949bdaaa577ab7d2f49782974a90efe909ea42c48be2eebeb'
protocol=json.loads((root/'run_protocol.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==protocol['expected_boot_id']
for row in protocol['payload_files']:
 path=root/row['file'];assert sha(path)==row['sha256'];ast.parse(path.read_text())
for row in protocol['runtime_files']:assert sha(Path(row['file']))==row['sha256']
assert PL.bitfile_name and sha(Path(PL.bitfile_name))==protocol['O8_bit_sha256']
with Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('rb')as stream:
 fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(stream,fcntl.LOCK_UN)
with(root/'controller.log').open('xb')as log:
 child=subprocess.Popen(['/usr/local/share/pynq-venv/bin/python3','-u',str(root/'board_controller.py')],
                         stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                         env={**os.environ,'XILINX_XRT':'/usr','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
value={'status':'FOUR_STARTUP_DIAGNOSTIC_PARENTS_LAUNCHED_ONCE','PID':child.pid,
       'boot_id':protocol['expected_boot_id'],'protocol_sha256':sha(root/'run_protocol.json'),
       'maximum_board_image_forwards':4,'PL_programmed_by_launch':False}
(root/'launch.json').write_bytes((json.dumps(value,indent=2)+'\n').encode());print(json.dumps(value),flush=True)
PY
