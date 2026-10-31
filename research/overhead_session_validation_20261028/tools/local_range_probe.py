from pathlib import Path
from urllib.request import Request,urlopen
import hashlib,json,time
ROOT=Path(__file__).resolve().parents[1]
u='https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/Sub-levels/Identification/Videos/2020-03-08_12-52-4/RGB.avi'
start=time.monotonic()
try:
    with urlopen(Request(u,headers={'Range':'bytes=0-262143','Accept-Encoding':'identity'}),timeout=20) as r:
        assert r.status==206
        b=r.read(262145);assert len(b)==262144
        result={'status':'BOUNDED_LOCAL_RANGE_PROBE_PASSED','source_url':u,'http_status':r.status,'Content-Range':r.headers['Content-Range'],
                'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'elapsed_s':time.monotonic()-start}
except Exception as exc:result={'status':'PROBE_FAILED','error':repr(exc),'elapsed_s':time.monotonic()-start}
out=ROOT/'evidence/local_range_probe.json';assert not out.exists();out.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
