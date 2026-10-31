"""Fetch small official directory metadata; no video/image bulk download."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import build_opener,ProxyHandler,Request
from urllib.parse import urljoin,unquote,urlsplit
import json,hashlib,time

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline')
OUT=ROOT/'catalog';OUT.mkdir(parents=True,exist_ok=True)
BASE='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/'
opener=build_opener(ProxyHandler({}))
class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            value=dict(attrs).get('href')
            if value:self.hrefs.append(value)
def fetch(suffix):
    url=urljoin(BASE,suffix)
    assert url.startswith(BASE)
    with opener.open(Request(url,headers={'User-Agent':'cattle-research-metadata/1.0'}),timeout=25) as response:
        data=response.read(3*1024*1024)
    parser=Links();parser.feed(data.decode('utf-8'))
    name=suffix.strip('/').replace('/','_')+'.html'
    (OUT/name).write_bytes(data)
    return parser.hrefs,{'url':url,'file':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
records=[];days={}
for day in ['2023Aug14','2023Aug19','2023Aug20']:
    links,record=fetch(day+'/');records.append(record)
    identities=sorted({unquote(urlsplit(h).path).rstrip('/').split('/')[-1] for h in links
                       if unquote(urlsplit(h).path).rstrip('/').split('/')[-1].isdigit()})
    days[day]=identities
common=sorted(set.intersection(*(set(v) for v in days.values())))
assert common,'No stable folder intersection'
sample_id=common[0]
samples={}
for day in days:
    links,record=fetch(f'{day}/{sample_id}/');records.append(record)
    images=sorted({urljoin(BASE+f'{day}/{sample_id}/',h) for h in links if urlsplit(h).path.lower().endswith(('.jpg','.jpeg'))})
    assert all(url.startswith(BASE+f'{day}/{sample_id}/') for url in images)
    samples[day]={'id':sample_id,'image_files':len(images),'example_urls':images[:8]}
result={'source':BASE,'day_folder_ids':days,'intersection_ids':common,'inspected_identity':sample_id,
        'sample_directories':samples,'catalog_files':records,
        'status':'Metadata only; stable identity semantics checked separately against author paper/loader'}
(OUT/'discovery.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'day_counts':{k:len(v) for k,v in days.items()},'intersection_count':len(common),'sample':samples},indent=2),flush=True)
