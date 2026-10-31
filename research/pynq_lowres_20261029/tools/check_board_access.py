"""Direct TCP access gate; no authentication, inference, reboot or PL access."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,socket,json,subprocess,sys
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();file=Path(a.output);assert not file.exists()
r={'created_UTC':datetime.now(timezone.utc).isoformat(),'host':'192.168.2.99','ports':[],
   'model_or_overlay_actions':0,'existing_PID8082_state':'NOT_OBSERVED'}
for port in [22,9090]:
    s=socket.socket();s.settimeout(3)
    try:s.connect(('192.168.2.99',port));row={'port':port,'TCP_connect':True}
    except Exception as e:row={'port':port,'TCP_connect':False,'error_type':type(e).__name__,'detail':str(e)}
    finally:s.close()
    r['ports'].append(row)
run=subprocess.run(['ping','-n','2','-w','1000','192.168.2.99'],capture_output=True,text=True,errors='replace')
r['ping_exit_code']=run.returncode;r['ping_output']=run.stdout
r['services_TCP_accessible']=all(x['TCP_connect'] for x in r['ports'])
r['status']='TCP_GATE_PASS_AUTHENTICATION_NOT_YET_VERIFIED' if r['services_TCP_accessible'] else 'TCP_GATE_RED_BOARD_SERVICES_UNREACHABLE'
file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,ensure_ascii=True));sys.exit(0 if r['services_TCP_accessible'] else 2)
