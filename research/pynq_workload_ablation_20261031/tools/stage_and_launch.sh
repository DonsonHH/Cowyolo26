set -euo pipefail
test "$(id -un)" = root
XILINX_XRT=/usr /usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import hashlib,json,os,tarfile,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
assert root.is_dir()and not(root/'launch.json').exists()and not(root/'results').exists()
archive=root/'workload_input_v2.tar.gz'
assert archive.stat().st_size==28389 and hashlib.sha256(archive.read_bytes()).hexdigest()=='23516da83090b6d8b012e584a08e62de2c6ce19013df21c17b58943c8845f56d'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==6
 for member in members:
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  dest=root/member.name;assert not dest.exists();dest.write_bytes(tar.extractfile(member).read())
p=json.loads((root/'run_protocol.json').read_text())
assert hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest()=='9329f1fc27a2059ffbddd459b289b69061d9f05f4f51e1e1ca840e5528456cb8'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==p['expected_boot_id']
for row in p['payload_files']:
 assert hashlib.sha256((root/row['file']).read_bytes()).hexdigest()==row['sha256']
for row in p['runtime_files']:
 assert hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()==row['sha256']
with(root/'run.log').open('xb')as output:
 task=subprocess.Popen(['/usr/local/share/pynq-venv/bin/python3','-u',str(root/'board_workload_ablation.py')],
                       cwd=root,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True,
                       env={**os.environ,'XILINX_XRT':'/usr','PYTHONDONTWRITEBYTECODE':'1'})
launch={'status':'EIGHT_WORKLOAD_CONDITIONS_LAUNCHED_ONCE','PID':task.pid,'created_board_UTC':datetime.now(timezone.utc).isoformat(),
        'boot_id':p['expected_boot_id'],'protocol_sha256':hashlib.sha256((root/'run_protocol.json').read_bytes()).hexdigest(),
        'explicit_original_O8_programming_planned_for_new_experiment':True,'max_model_image_forwards':3208,'whole_goal_complete':False}
(root/'launch.json').write_bytes((json.dumps(launch,indent=2)+'\n').encode());print(json.dumps(launch),flush=True)
PY
