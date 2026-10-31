set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
"$PROJECT/env/bin/python" - <<'PY'
import socket,json,time
from urllib.request import Request,build_opener,ProxyHandler
ports=[]
for port in [2080,27831]:
    try:
        s=socket.create_connection(('127.0.0.1',port),timeout=1);s.close();ports.append(port)
    except OSError:pass
result={'existing_loopback_proxy_ports':ports,'probes':[]}
for port in ports:
    start=time.monotonic()
    try:
        op=build_opener(ProxyHandler({'http':f'http://127.0.0.1:{port}','https':f'http://127.0.0.1:{port}'}))
        # Read-only health and a bounded file range; no node or selector changes.
        with op.open('https://ipinfo.io/json',timeout=12) as r:country=json.loads(r.read(8192))['country']
        url='https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Videos/2020-03-08_12-52-4/RGB.avi'
        with op.open(Request(url,headers={'Range':'bytes=0-262143','Accept-Encoding':'identity'}),timeout=18) as r:
            status=r.status;cr=r.headers.get('Content-Range');body=r.read(262145)
            assert status==206 and len(body)==262144
        result['probes'].append({'port':port,'country_only':country,'range_bytes':len(body),'status':status,'Content-Range':cr,'elapsed_s':time.monotonic()-start})
    except Exception as exc:result['probes'].append({'port':port,'error':repr(exc),'elapsed_s':time.monotonic()-start})
print(json.dumps(result))
PY
