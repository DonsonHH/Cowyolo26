set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,os,subprocess,glob,pynq
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
processes=[]
for key in ['probe192','formal192','formal256','formal320','input_probe','stream_replay','framebank_replay']:
    launch=json.loads((root/('launch_'+key+'.json')).read_text());pid=launch['PID']
    processes.append({'run':key,'PID':pid,'proc_exists':(Path('/proc')/str(pid)).exists(),'terminal':json.loads((root/key/'terminal.json').read_text())})
assert all(not p['proc_exists'] for p in processes)
for relative in ['protocol.json','input_gate.json','stream_protocol.json','framebank_protocol.json','board_profile.py','board_input_probe.py','board_stream_replay.py','board_framebank_replay.py']:
    assert (root/relative).is_file()
bit=pynq.PL.bitfile_name;assert bit and Path(bit).is_file()
state={'status':'ALL7_OWN_BOARD_PROCESSES_TERMINAL_AND_ABSENT_SSH_READ_CONFIRMED','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
  'pynq_version':pynq.__version__,'uid':os.getuid(),'machine':os.uname().machine,'actual_IPs':subprocess.check_output(['hostname','-I'],text=True),
  'services':subprocess.check_output(['systemctl','is-active','ssh','jupyter'],text=True),'processes':processes,
  'PL_after_bitfile':bit,'PL_after_bit_sha256':sha(bit),'PL_after_hwh_sha256':sha(Path(bit).with_suffix('.hwh')),
  'PL_IP_names':list(pynq.PL.ip_dict),'memory':Path('/proc/meminfo').read_text(),'camera_device_paths':glob.glob('/dev/video*'),
  'no_new_inference_or_programming_in_this_read':True,'board_wall_clock_not_used_for_latency':True,
  'task_runtime_hashes':{r:sha(root/r) for r in ['protocol.json','input_gate.json','stream_protocol.json','framebank_protocol.json','board_profile.py','board_input_probe.py','board_stream_replay.py','board_framebank_replay.py']},
  'kernel_tail':subprocess.run(['journalctl','-k','-b','--no-pager','-n','30'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True).stdout,
  'foreground_background_joint5FPS_proven':False,'current_cow_finetuned_weights_deployed':False,'whole_goal_complete':False}
print(json.dumps(state))
PY
