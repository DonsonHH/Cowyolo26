set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,os,subprocess,tarfile
from pynq import PL,Overlay
root=Path('/home/xilinx/jupyter_notebooks/cow_research_parent_only_workload_20261031')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'parent_only_input_v1.tar.gz'
assert not(root/'launch.json').exists() and not(root/'results').exists()
assert archive.stat().st_size==28246 and sha(archive)=='fff2d926d629b3c11fb712b86ebc6958572ba38fd15e7fdaa6292ceeed69c67d'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==len({row.name for row in members})==6
 for row in members:
  path=PurePosixPath(row.name);assert row.isfile() and not path.is_absolute() and len(path.parts)==1
  target=root/row.name;assert not target.exists();target.write_bytes(tar.extractfile(row).read())
assert sha(root/'run_protocol.json')=='7e2d82a5d6af9d67414544fd896b3c7cf73095d43304f097c12ecd48ddddd97a'
p=json.loads((root/'run_protocol.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==p['expected_boot_id']
for row in p['payload_files']:assert sha(root/row['file'])==row['sha256'];ast.parse((root/row['file']).read_text())
for row in p['runtime_files']:assert sha(Path(row['file']))==row['sha256']
prior=Path('/home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031')
previous=json.loads((prior/'final_state.json').read_text())
assert previous['actual_identity_warmups']==4 and previous['hardware']['core_error']=='0x0'
for pid in[previous['controller_PID']]+[row[key]for row in previous['processes']for key in['parent_PID','worker_PID']]:
 assert not(Path('/proc')/str(pid)).exists()
collection=json.loads((prior/'collection_launch.json').read_text());assert not(Path('/proc')/str(collection['PID'])).exists()
with Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('rb')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
assert PL.bitfile_name and sha(Path(PL.bitfile_name))==p['O8_bit_sha256']
overlay=Overlay(PL.bitfile_name,download=False)
hardware={'core_error':hex(overlay.conv_accel_0.read(0x64)),
          'DMA_MM2S':hex(overlay.axi_dma_0.read(4)),'DMA_S2MM':hex(overlay.axi_dma_0.read(0x34))}
assert hardware['core_error']=='0x0' and not((int(hardware['DMA_MM2S'],16)|int(hardware['DMA_S2MM'],16))&0x770)
preflight={'status':'PARENT_ONLY_FULL_WORKLOAD_RUNTIME_AND_PREVIOUS_TASK_TERMINAL_PREFLIGHT',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'boot_id':boot,'PL_bitfile_name':PL.bitfile_name,
 'PL_SHA256':sha(Path(PL.bitfile_name)),'hardware':hardware,'meminfo':Path('/proc/meminfo').read_text(),
 'vmstat':Path('/proc/vmstat').read_text(),'PL_programmed':False,'new_model_forwards':0}
(root/'preflight.json').write_bytes((json.dumps(preflight,indent=2)+'\n').encode())
with(root/'run.log').open('xb')as log:
 child=subprocess.Popen(['/usr/local/share/pynq-venv/bin/python3','-u',str(root/'board_workload_ablation.py')],
   stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
   env={**os.environ,'XILINX_XRT':'/usr','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
value={'status':'PARENT_ONLY_FULL_EIGHT_WORKLOAD_CASES_LAUNCHED_ONCE','PID':child.pid,'boot_id':boot,
       'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(root/'run_protocol.json'),
       'maximum_board_image_forwards':3208}
(root/'launch.json').write_bytes((json.dumps(value,indent=2)+'\n').encode());print(json.dumps(value),flush=True)
PY
