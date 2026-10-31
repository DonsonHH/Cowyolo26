set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import ast,fcntl,hashlib,json,os,subprocess,tarfile
from pynq import PL,Overlay
root=Path('/home/xilinx/jupyter_notebooks/cow_research_parent_only_trigger_20261031');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'parent_only_trigger_input_v1.tar.gz'
assert not(root/'launch.json').exists()and not(root/'results').exists()
assert archive.stat().st_size==15704 and sha(archive)=='540ca3d3484817c31662a24eac03f18f90a0767c5bd160d83d852a98bb2d6e9c'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==len({row.name for row in members})==6
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and len(rel.parts)==1
  path=root/row.name;assert not path.exists();path.write_bytes(tar.extractfile(row).read())
assert sha(root/'run_protocol.json')=='17e08b19b38d438351e005ecc6fa90256f65b7ec8f780aa517449d7c3856af4c'
p=json.loads((root/'run_protocol.json').read_text());boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==p['expected_boot_id']
for row in p['payload_files']:assert sha(root/row['file'])==row['sha256'];ast.parse((root/row['file']).read_text())
for row in p['runtime_files']:assert sha(Path(row['file']))==row['sha256']
manifest=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030/board_input_manifest.json')
assert sha(manifest)=='7f316114c1eb654cbaf34c5e401119c87a1ce125899930ca3439ddc8fbc5380c'
assert PL.bitfile_name and sha(Path(PL.bitfile_name))==p['O8_bit_sha256']
with Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('rb')as f:
 fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
o=Overlay(PL.bitfile_name,download=False)
hardware={'core_error':hex(o.conv_accel_0.read(0x64)),'DMA_MM2S':hex(o.axi_dma_0.read(4)),'DMA_S2MM':hex(o.axi_dma_0.read(0x34))}
assert hardware['core_error']=='0x0'and not((int(hardware['DMA_MM2S'],16)|int(hardware['DMA_S2MM'],16))&0x770)
pre={'status':'PARENT_ONLY_TRIGGER_RUNTIME_SOURCE_AND_EXISTING_O8_VERIFIED_BEFORE_LAUNCH',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'boot_id':boot,'PL_bitfile_name':PL.bitfile_name,
 'PL_SHA256':sha(Path(PL.bitfile_name)),'input_manifest_sha256':sha(manifest),'hardware':hardware,
 'meminfo':Path('/proc/meminfo').read_text(),'vmstat':Path('/proc/vmstat').read_text(),
 'new_model_forwards':0,'PL_programmed':False}
(root/'preflight.json').write_bytes((json.dumps(pre,indent=2)+'\n').encode())
with(root/'run.log').open('xb')as log:
 child=subprocess.Popen(['/usr/local/share/pynq-venv/bin/python3','-u',str(root/'board_trigger_repeats.py')],
                         stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                         env={**os.environ,'XILINX_XRT':'/usr','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'})
value={'status':'PARENT_ONLY_FOUR_ACTUAL_COUNT_TRIGGER_CASES_LAUNCHED_ONCE','PID':child.pid,'boot_id':boot,
       'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(root/'run_protocol.json'),
       'maximum_board_image_forwards':1652}
(root/'launch.json').write_bytes((json.dumps(value,indent=2)+'\n').encode());print(json.dumps(value),flush=True)
PY
