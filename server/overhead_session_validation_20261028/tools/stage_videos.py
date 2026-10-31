"""Network staging only on mu01; no media decode or model execution here."""
from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,time,socket,os

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_session_validation_20261028')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert socket.gethostname()=='mu01' and os.environ['HOME']=='/share/home/renly'
    protocol=ROOT/'protocol/sessions_v1.json';p=json.loads(protocol.read_text());data=ROOT/'data';data.mkdir(exist_ok=False)
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    def fetch(row):
        out=data/row['sequence'];out.mkdir();dest=out/'RGB.avi';partial=out/'RGB.avi.partial';start=time.time()
        try:
            opener=build_opener(ProxyHandler({}))
            with opener.open(Request(row['url'],headers={'User-Agent':'ID-Coo ordinary-overhead research'}),timeout=35) as r:
                assert r.status==200 and urlparse(r.url).hostname=='data.bris.ac.uk'
                expected=int(r.headers.get('Content-Length','0'));assert expected<=p['maximum_each_video_bytes']
                digest=hashlib.sha256();count=0
                with partial.open('xb') as f:
                    while block:=r.read(1024*1024):
                        count+=len(block);assert count<=p['maximum_each_video_bytes'];f.write(block);digest.update(block)
                assert count>0 and (not expected or count==expected)
            partial.rename(dest)
            record={**row,'status':'DOWNLOADED','path':str(dest),'bytes':count,'Content-Length':expected,
                    'sha256':digest.hexdigest(),'elapsed_s':time.time()-start}
        except Exception as exc:
            record={**row,'status':'FAILED','error':repr(exc),'partial_retained':partial.exists(),'elapsed_s':time.time()-start}
        (out/'fetch_record.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True);return record
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(fetch,p['selected']))
    result={'status':'FOUR_FROZEN_SESSIONS_TRANSFER_ATTEMPTED','protocol_sha256':sha(protocol),'files':results,
            'successful':sum(r['status']=='DOWNLOADED' for r in results),'successful_bytes':sum(r.get('bytes',0) for r in results),
            'media_decode_on_login_node':False,'model_run_on_login_node':False}
    assert result['successful_bytes']<=p['maximum_total_video_bytes']
    (evidence/'fetch_manifest.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='files'}),flush=True)
    assert result['successful']==4,'Failures retained; do not silently swap selected videos'

if __name__=='__main__':main()
