"""Discover only the user-authorized directly connected192.168.2.0/24 link."""
from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import argparse,socket,json,time
p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();file=Path(a.output);assert not file.exists()
started=time.monotonic();targets=[('192.168.2.'+str(i),port) for i in range(2,255) for port in [22,9090]]
def probe(item):
    host,port=item;s=socket.socket();s.settimeout(.4)
    try:
        s.connect((host,port));return {'host':host,'port':port,'TCP_connect':True}
    except OSError:return None
    finally:s.close()
with ThreadPoolExecutor(max_workers=32) as executor:results=[r for r in executor.map(probe,targets) if r]
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'scope':'UserauthorizeddirectEthernet192.168.2.0/24only',
        'ports':[22,9090],'probes':len(targets),'timeout_s':.4,'open_services':results,'elapsed_s':time.monotonic()-started,
        'authentication_attempts':0,'network_configuration_changes':0,'board_model_or_PL_actions':0}
file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
