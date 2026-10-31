"""Stage a predeclared, identity-disjoint training study from public directories."""
from pathlib import Path
from urllib.request import build_opener,ProxyHandler,Request
from urllib.error import HTTPError
from urllib.parse import urljoin,urlsplit
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json,shutil,time

BASE='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/'
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'identity_training'
OUT=ROOT/'catalog';OUT.mkdir(parents=True,exist_ok=True)
protocol_path=ROOT/'protocol/identity_training_v1.json';p=json.loads(protocol_path.read_text())
roles=['training_ids','validation_registered_ids','validation_unknown_ids','evaluation_registered_ids','evaluation_unknown_ids']
assert sum(len(p[k]) for k in roles)==len(set().union(*(set(p[k]) for k in roles)))
class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a' and dict(attrs).get('href'):self.hrefs.append(dict(attrs)['href'])
def fetch(url,allow_missing=False):
    for attempt in range(3):
        try:
            with build_opener(ProxyHandler({})).open(Request(url,headers={'User-Agent':'cattle-research-small-training/1.0'}),timeout=30) as response:data=response.read(4*1024*1024)
            return data
        except HTTPError as e:
            if e.code==404 and allow_missing:return None
            if attempt==2:raise
        except Exception:
            if attempt==2:raise
        time.sleep(1+attempt)
tasks=set()
for identity in p['training_ids']:
    for day in p['data_roles']['train']['days']:tasks.add((day,identity))
for role,days in [('validation_registered_ids',['2023Aug14','2023Aug18']),('validation_unknown_ids',['2023Aug18']),('evaluation_registered_ids',['2023Aug14','2023Aug20']),('evaluation_unknown_ids',['2023Aug20'])]:
    for identity in p[role]:
        for day in days:tasks.add((day,identity))
def listing(day,identity):
    directory=BASE+f'{day}/{identity}/';dest=OUT/'directories'/f'{day}_{identity}.html';dest.parent.mkdir(exist_ok=True)
    if dest.exists():data=dest.read_bytes()
    else:
        data=fetch(directory,True)
        if data is not None:dest.write_bytes(data)
    if data is None:return (day,identity),[]
    parser=Links();parser.feed(data.decode('utf-8'))
    files=sorted({urljoin(directory,url) for url in parser.hrefs if urlsplit(url).path.endswith('_1.jpg')})
    assert all(url.startswith(directory) for url in files)
    return (day,identity),files
directories={}
with ThreadPoolExecutor(max_workers=4) as pool:
    for future in as_completed([pool.submit(listing,*task) for task in sorted(tasks)]):key,files=future.result();directories[key]=files
rows=[];excluded=[];eligible={role:[] for role in roles}
def chosen(files,limit):
    if len(files)<=limit:return list(enumerate(files))
    indices=[round(i*(len(files)-1)/(limit-1)) for i in range(limit)]
    return [(i,files[i]) for i in indices]
def add(role,identity,day,split,limit):
    files=directories[(day,identity)]
    for index,url in chosen(files,limit):
        name=urlsplit(url).path.split('/')[-1]
        rows.append({'identity':identity,'role':role,'day':day,'camera':1,'split':split,'url':url,
                     'source_filename':name,'source_index':index,'source_sequence_length':len(files),
                     'relative_path':f'data/{day}/{identity}/{name}'})
for identity in p['training_ids']:
    days=p['data_roles']['train']['days'];available=[d for d in days if directories[(d,identity)]]
    n=sum(min(10,len(directories[(d,identity)])) for d in days)
    if len(available)<2 or n<10:excluded.append({'identity':identity,'role':'training_ids','reason':'Insufficient training dates/images','dates':available,'images':n});continue
    eligible['training_ids'].append(identity)
    for day in days:add('training_ids',identity,day,'train',10)
for role,required in [('validation_registered_ids',[('2023Aug14','validation_gallery'),('2023Aug18','validation_query')]),
                      ('validation_unknown_ids',[('2023Aug18','validation_query')]),
                      ('evaluation_registered_ids',[('2023Aug14','evaluation_gallery'),('2023Aug20','evaluation_query')]),
                      ('evaluation_unknown_ids',[('2023Aug20','evaluation_query')])]:
    for identity in p[role]:
        insufficient=[{'day':day,'images':len(directories[(day,identity)])} for day,_ in required if len(directories[(day,identity)])<5]
        if insufficient:excluded.append({'identity':identity,'role':role,'reason':'Fewer than5 required camera1 crops','details':insufficient});continue
        eligible[role].append(identity)
        for day,split in required:add(role,identity,day,split,5)
assert len(eligible['training_ids'])>=10
assert all(len(eligible[role])>=3 for role in roles[1:]),eligible
selection={'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),'eligible_roles':eligible,'excluded':excluded,'images':rows}
selection_path=OUT/'selection.json'
if selection_path.exists():assert json.loads(selection_path.read_text())==selection
else:selection_path.write_text(json.dumps(selection,indent=2))
print(json.dumps({'metadata_ready':True,'images':len(rows),'roles':{k:len(v) for k,v in eligible.items()},'exclusions':excluded}),flush=True)
def download(row):
    dest=ROOT/row['relative_path'];dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():data=dest.read_bytes();origin='existing_staged'
    else:
        old=PROJECT/'identity_baseline'/row['relative_path']
        if old.exists():data=old.read_bytes();origin='previous_public_download'
        else:data=fetch(row['url']);origin='university_download'
        assert data.startswith(b'\xff\xd8') and len(data)>1000
        temporary=dest.with_suffix('.jpg.partial');temporary.write_bytes(data);temporary.rename(dest)
    assert data.startswith(b'\xff\xd8') and len(data)>1000
    return {**row,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'transfer_origin':origin}
manifest=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    for i,future in enumerate(as_completed([pool.submit(download,row) for row in rows]),1):
        manifest.append(future.result())
        if i%50==0:print(json.dumps({'downloaded':i,'total':len(rows)}),flush=True)
manifest.sort(key=lambda r:r['relative_path'])
(OUT/'image_manifest.json').write_text(json.dumps(manifest,indent=2))
models=ROOT/'models';models.mkdir(exist_ok=True)
weight=PROJECT/'identity_baseline/models/mobilenet_v3_small-047dcff4.pth'
assert hashlib.sha256(weight.read_bytes()).hexdigest()==p['checkpoint_sha256']
target=models/weight.name
if not target.exists():shutil.copy2(weight,target)
status={'status':'STAGED_PENDING_IMAGE_AUDIT','images':len(manifest),'bytes':sum(r['bytes'] for r in manifest),
        'protocol_sha256':selection['protocol_sha256'],'manifest_sha256':hashlib.sha256((OUT/'image_manifest.json').read_bytes()).hexdigest(),
        'eligible_roles':eligible,'excluded':excluded,'model_sha256':p['checkpoint_sha256']}
(OUT/'stage_complete.json').write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)
