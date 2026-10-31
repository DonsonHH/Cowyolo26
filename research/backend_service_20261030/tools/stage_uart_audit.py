from pathlib import Path
import json,base64,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
script=ROOT/'tools/audit_board_files_recovery.py';raw=script.read_bytes();digest=hashlib.sha256(raw).hexdigest()
destination='/home/xilinx/jupyter_notebooks/cow_research_backend_serial_recovery_20261030/audit_board_files_recovery.py'
body="python3 -c 'from pathlib import Path; import base64,hashlib; p=Path(\""+destination+"\"); b=base64.b64decode(\""+base64.b64encode(raw).decode()+"\"); assert not p.exists() and hashlib.sha256(b).hexdigest()==\""+digest+"\"; f=p.open(\"xb\"); f.write(b); f.close(); print(\"AUDIT_SCRIPT_STAGED_HASH_VERIFIED\")'"
command=ROOT/'tools/serial_stage_audit.txt';assert not command.exists();command.write_text(body,encoding='utf-8')
subprocess.run([sys.executable,'-X','utf8',str(PROJECT/'pynq_lowres_20261029/tools/serial_command.py'),'--command-file',str(command),'--output',str(ROOT/'evidence/serial_audit_stage01.json'),'--timeout','20'],capture_output=True,check=True)
record=json.loads((ROOT/'evidence/serial_audit_stage01.json').read_text());assert record['status']=='SERIAL_COMMAND_COMPLETE' and record['exit_code']==0
launch="python3 -c 'from pathlib import Path; import subprocess,os,json; r=Path(\"/home/xilinx/jupyter_notebooks/cow_research_backend_serial_recovery_20261030\"); assert not (r/\"numeric_audit_launch.json\").exists(); log=(r/\"numeric_audit.log\").open(\"xb\"); p=subprocess.Popen([\"/usr/local/share/pynq-venv/bin/python3\",\"-u\",\"-B\",str(r/\"audit_board_files_recovery.py\")],stdout=log,stderr=subprocess.STDOUT,cwd=r,start_new_session=True); d={\"PID\":p.pid,\"scope\":\"read_only_no_forwards\"}; (r/\"numeric_audit_launch.json\").write_text(json.dumps(d)+\"\\n\"); print(json.dumps(d))'"
command=ROOT/'tools/serial_launch_audit.txt';assert not command.exists();command.write_text(launch,encoding='utf-8')
subprocess.run([sys.executable,'-X','utf8',str(PROJECT/'pynq_lowres_20261029/tools/serial_command.py'),'--command-file',str(command),'--output',str(ROOT/'evidence/serial_audit_launch01.json'),'--timeout','20'],capture_output=True,check=True)
record=json.loads((ROOT/'evidence/serial_audit_launch01.json').read_text());assert record['status']=='SERIAL_COMMAND_COMPLETE' and record['exit_code']==0
print(json.dumps({'staged_script_SHA256':digest,'launch':record['output'][-800:],'remote_experiment_rerun':False}))
