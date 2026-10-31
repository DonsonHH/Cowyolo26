from pathlib import Path
from urllib.request import build_opener,ProxyHandler,Request
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,time
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis');protocol=ROOT/'protocol/future_comparison_frozen.json'
p=json.loads(protocol.read_text());rows=p['source_entries']
assert len(rows)==90 and len(p['conditions'])==9
for c in p['conditions']:assert hashlib.sha256(Path(c['model_path']).read_bytes()).hexdigest()==c['model_sha256']
def download(row):
    url=row['source_url'];assert url.startswith('https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/')
    relative=f'holdout_data/{row["day"]}/{row["identity"]}/{url.split("/")[-1]}'
    path=ROOT/relative;path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():data=path.read_bytes()
    else:
        for attempt in range(3):
            try:
                with build_opener(ProxyHandler({})).open(Request(url,headers={'User-Agent':'cattle-untouched-holdout/1.0'}),timeout=30) as response:data=response.read(2*1024*1024)
                break
            except Exception:
                if attempt==2:raise
                time.sleep(attempt+1)
        assert data.startswith(b'\xff\xd8') and len(data)>1000
        temporary=path.with_suffix('.jpg.partial');temporary.write_bytes(data);temporary.rename(path)
    return {**row,'relative_path':relative,'split':'gallery' if row['day']=='2023Aug14' else 'query',
            'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
manifest=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    for i,future in enumerate(as_completed([pool.submit(download,r) for r in rows]),1):
        manifest.append(future.result())
        if i%15==0:print(json.dumps({'downloaded':i,'total':len(rows)}),flush=True)
manifest.sort(key=lambda r:r['relative_path']);out=ROOT/'catalog/future_holdout'
(out/'image_manifest.json').write_text(json.dumps(manifest,indent=2))
record={'status':'STAGED_PENDING_PIXEL_AUDIT','images':len(manifest),'bytes':sum(r['bytes'] for r in manifest),
        'frozen_protocol_sha256':hashlib.sha256(protocol.read_bytes()).hexdigest(),
        'manifest_sha256':hashlib.sha256((out/'image_manifest.json').read_bytes()).hexdigest(),'model_forward_performed':False}
(out/'stage_complete.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
