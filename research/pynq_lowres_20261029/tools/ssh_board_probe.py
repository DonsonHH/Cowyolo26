from pathlib import Path
from datetime import datetime,timezone
import sys,json,base64,hashlib,argparse,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tool_deps'));import paramiko
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);assert not out.exists()
inventory=json.loads((ROOT/'evidence/board_project_inventory.json').read_text());obj=json.loads(''.join(r['content'].get('text','') for r in inventory['messages'] if r['type']=='stream'))
public=obj['ssh_public_host_key'].split();assert public[0]=='ssh-ed25519';key=paramiko.Ed25519Key(data=base64.b64decode(public[1]))
client=paramiko.SSHClient();client.get_host_keys().add('192.168.2.99','ssh-ed25519',key);client.set_missing_host_key_policy(paramiko.RejectPolicy())
password=sys.stdin.readline().rstrip('\r\n');record={'created_UTC':datetime.now(timezone.utc).isoformat(),'host':'192.168.2.99','username':'xilinx',
'host_fingerprint_SHA256':'SHA256:'+base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('='),'host_key_source':'ReadviauserauthorizedJupyterbeforebenchmark','authentication_material_saved':False}
try:
    client.connect('192.168.2.99',username='xilinx',password=password,look_for_keys=False,allow_agent=False,timeout=6,banner_timeout=6,auth_timeout=6)
    del password
    command="id -un; hostname; uname -m; cat /proc/uptime; free -m; ps -p 8082 -o pid,ppid,state,etimes,rss,comm; cat /home/xilinx/jupyter_notebooks/cow_research_lowres_20261029/results/progress.json; tail -n 8 /home/xilinx/jupyter_notebooks/cow_research_lowres_20261029/benchmark.log"
    _,stdout,stderr=client.exec_command(command,timeout=10);record.update({'status':'SSH_CONNECTED','stdout':stdout.read().decode('utf-8','replace')[:12000],'stderr':stderr.read().decode('utf-8','replace')[:1500],'exit':stdout.channel.recv_exit_status()})
except Exception as e:record.update({'status':'SSH_UNAVAILABLE','error_type':type(e).__name__,'detail':str(e)[:300]})
finally:client.close()
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
