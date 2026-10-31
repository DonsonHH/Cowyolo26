"""Bounded, deterministic cross-day sample from the university's public data."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import build_opener,ProxyHandler,Request
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,time,sys

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline')
BASE='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/'
protocol_path=ROOT/'protocol/identity_pilot_v1.json';protocol=json.loads(protocol_path.read_text())
class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            href=dict(attrs).get('href')
            if href:self.hrefs.append(href)
def request(url,limit=20*1024*1024):
    for attempt in range(3):
        try:
            opener=build_opener(ProxyHandler({}))
            with opener.open(Request(url,headers={'User-Agent':'cattle-research-small-sample/1.0'}),timeout=30) as r:
                data=r.read(limit+1)
            if len(data)>limit:raise ValueError('Unexpectedly large metadata/image response')
            return data
        except Exception:
            if attempt==2:raise
            time.sleep(1+attempt)

metadata=ROOT/'catalog/sample_directories';metadata.mkdir(parents=True,exist_ok=True)
def listing(day,identity):
    suffix=f'{day}/{identity}/';url=BASE+suffix;path=metadata/f'{day}_{identity}.html'
    if path.exists():data=path.read_bytes()
    else:data=request(url,3*1024*1024);path.write_bytes(data)
    parser=Links();parser.feed(data.decode('utf-8'))
    files=sorted({urljoin(url,h) for h in parser.hrefs if urlsplit(h).path.endswith('_1.jpg')})
    assert all(f.startswith(url) for f in files)
    return (day,identity),files

tasks=[]
for identity in protocol['known_ids']:
    for day in ['2023Aug14','2023Aug19','2023Aug20']:tasks.append((day,identity))
tasks.extend(('2023Aug19',i) for i in protocol['validation_unknown_ids'])
tasks.extend(('2023Aug20',i) for i in protocol['evaluation_unknown_ids'])
directories={}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(listing,*pair) for pair in tasks]
    for future in as_completed(futures):key,files=future.result();directories[key]=files
excluded=[];eligible=[];rows=[]
cohorts=[('known',protocol['known_ids'],['2023Aug14','2023Aug19','2023Aug20']),
         ('validation_unknown',protocol['validation_unknown_ids'],['2023Aug19']),
         ('evaluation_unknown',protocol['evaluation_unknown_ids'],['2023Aug20'])]
for cohort,identities,days in cohorts:
    for identity in identities:
        insufficient=[{'day':day,'camera1_images':len(directories[(day,identity)])} for day in days if len(directories[(day,identity)])<5]
        if insufficient:excluded.append({'identity':identity,'cohort':cohort,'reason':'Fewer than five camera1 crops in a required date','details':insufficient});continue
        eligible.append({'identity':identity,'cohort':cohort})
        for day in days:
            files=directories[(day,identity)];indices=[round(i*(len(files)-1)/4) for i in range(5)]
            assert len(set(indices))==5
            for index in indices:
                url=files[index];split='gallery' if day=='2023Aug14' else 'calibration' if day=='2023Aug19' else 'evaluation'
                rows.append({'identity':identity,'cohort':cohort,'split':split,'day':day,'camera':1,
                             'url':url,'source_filename':urlsplit(url).path.split('/')[-1],
                             'source_index_in_camera_sequence':index,'source_camera_sequence_length':len(files),
                             'relative_path':f'data/{day}/{identity}/{urlsplit(url).path.split("/")[-1]}'})
selection={'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),'eligible_identities':eligible,'excluded_identities':excluded,'images':rows}
selection_path=ROOT/'catalog/selection.json'
if selection_path.exists():assert json.loads(selection_path.read_text())==selection,'Deterministic selection changed'
else:selection_path.write_text(json.dumps(selection,indent=2))
print(json.dumps({'metadata_ready':True,'selected_images':len(rows),'eligible_identities':len(eligible),'excluded':excluded}),flush=True)

def download(row):
    path=ROOT/row['relative_path'];path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():data=path.read_bytes()
    else:
        data=request(row['url']);temporary=path.with_suffix('.jpg.partial');temporary.write_bytes(data);temporary.rename(path)
    assert data.startswith(b'\xff\xd8') and len(data)>1000,'Not a plausible JPEG response'
    return {**row,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
manifest=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(download,row) for row in rows]
    for i,future in enumerate(as_completed(futures),1):
        manifest.append(future.result())
        if i%50==0:print(json.dumps({'downloaded':i,'total':len(rows)}),flush=True)
manifest.sort(key=lambda r:r['relative_path'])
(ROOT/'catalog/image_manifest.json').write_text(json.dumps(manifest,indent=2))
author_url='https://raw.githubusercontent.com/Phoenix4582/CowIDentifier/main/Supervised/datasets/MultiCamCows/MultiCamCows.py'
author=request(author_url,256*1024);(ROOT/'catalog/author_loader.py.txt').write_bytes(author)
status={'status':'STAGED_NOT_IMAGE_AUDITED','images':len(manifest),'bytes':sum(r['bytes'] for r in manifest),
        'cohorts':{cohort:sum(e['cohort']==cohort for e in eligible) for cohort,_,_ in cohorts},
        'protocol_sha256':selection['protocol_sha256'],'manifest_sha256':hashlib.sha256((ROOT/'catalog/image_manifest.json').read_bytes()).hexdigest(),
        'author_loader_source':author_url,'author_loader_sha256':hashlib.sha256(author).hexdigest(),
        'licence_source':'https://data.bris.ac.uk/data/dataset/2inu67jru7a6821kkgehxg3cv2',
        'licence_label':'Non-Commercial Government Licence for public sector information',
        'timing':'No model inference or performance-based image selection during staging'}
(ROOT/'catalog/stage_complete.json').write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)
