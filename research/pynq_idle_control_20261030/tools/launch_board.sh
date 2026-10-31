set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,os,sys,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_idle_control_20261030');old=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030')
t=json.loads((old/'results/terminal.json').read_text());assert t['status']=='BOTH392_SLOT_PERIODIC_FRONTEND_CASES_AND_ACTUAL_TRIGGERED_BACKGROUND_COMPLETE' and not (Path('/proc')/str(t['PID'])).exists()
archive=root/'payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='07a255ef26be1ad606d536e91be501561ce49706e2208684214832c56cd02243'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['protocol.json','board_idle.py','background_idle_worker.py']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_idle.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'cases':2,'slots_per_case':392,'actual_identity_process_SIGSTOP_SIGCONT_gate':True,'cached_identity_results_used':False}
(root/'launch.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
PY
