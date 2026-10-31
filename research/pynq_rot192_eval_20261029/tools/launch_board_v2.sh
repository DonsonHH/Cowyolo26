set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import os,sys,json,hashlib,tarfile,subprocess,fcntl
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029')
old=json.loads((root/'launch.json').read_text());assert old['PID']==25957 and not (Path('/proc')/str(old['PID'])).exists()
assert not (root/'results/record.json').exists() and not (root/'results/terminal.json').exists()
assert isinstance(PL.bitfile_name,str)
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
observed={'old_PID':old['PID'],'old_PID_absent':True,'PL_bitfile_type':type(PL.bitfile_name).__name__,'PL_bit_sha256':hashlib.sha256(Path(PL.bitfile_name).read_bytes()).hexdigest(),
 'old_results_files':sorted(p.name for p in (root/'results').iterdir()),'first_failed_script_forwards':0,
 'zero_forward_evidence':'Unconditional sha(PL.bitfile_name str) occurs before lock, NativeGraph construction and all run calls; process is absent and log finally repeats same helper error.'}
assert observed['PL_bit_sha256']=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
(root/'failed_v1_forensic.json').write_text(json.dumps(observed,indent=2)+'\n')
archive=root/'v2_patch.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='fe3a2683b773a554cb4bb3d5cb9a28dc292fd32ff64e71ae536f8843287eb6ed'
assert not (root/'launch_v2.json').exists() and not (root/'results_v2').exists()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['board_video_v2.py','board_protocol_v2.json']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
assert hashlib.sha256((root/'board_protocol_v2.json').read_bytes()).hexdigest()=='8edd83e313c0953fd1ed83397554bf53ab810b7730d849cf6d4488e69ffaecda'
with (root/'run_v2.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_video_v2.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'actual_video_model_forwards_expected':2654,'warmups':2,'counter_paths_expected':6,'old_failed_PID':25957}
(root/'launch_v2.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'preflight':observed,'launch':record}))
PY
