set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,socket
from pynq import PL
base=Path('/home/xilinx/jupyter_notebooks')
roots=['cow_research_o8_rot192_qual_20261029','cow_research_rot192_video_20261029','cow_research_numpy_tracker_20261029',
 'cow_research_ncnn_identity_20261029','cow_research_periodic_joint_20261030','cow_research_idle_control_20261030',
 'cow_research_capture_encoding_20261030','cow_research_o8_s256_qual_20261030','cow_research_o8_s320_qual_20261030']
rows=[]
for name in roots:
 root=base/name
 for f in sorted(root.glob('*launch*.json')):
  value=json.loads(f.read_text());pid=value.get('PID')
  if pid is not None:rows.append({'task':name,'launch_file':f.name,'PID':pid,'proc_exists':(Path('/proc')/str(pid)).exists()})
assert not any(r['proc_exists'] for r in rows)
def listening(port):
 s=socket.socket();s.settimeout(2)
 try:return s.connect_ex(('127.0.0.1',port))==0
 finally:s.close()
digest=hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest();assert digest=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
result={'status':'ALL_LISTED_OWN_LAUNCHED_PIDS_ABSENT_KNOWN_O8_LOADED_SSH_AND_JUPYTER_READ',
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'tasks':rows,'PL_bitfile':PL.bitfile_name,'PL_bit_sha256':digest,
 'memory':Path('/proc/meminfo').read_text(),'video_devices':[str(p) for p in Path('/dev').glob('video*')],
 'SSH22_listens':listening(22),'Jupyter9090_listens':listening(9090),'new_network_forwards':0,'new_PL_actions':0}
print(json.dumps(result))
PY
