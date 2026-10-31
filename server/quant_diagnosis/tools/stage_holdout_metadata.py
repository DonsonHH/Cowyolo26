"""Future holdout directory eligibility only; never fetch image bytes."""
from pathlib import Path
from urllib.request import build_opener,ProxyHandler,Request
from urllib.error import HTTPError
from urllib.parse import urljoin,urlsplit
from html.parser import HTMLParser
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib,json
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis');OUT=ROOT/'catalog/future_holdout';OUT.mkdir(parents=True,exist_ok=False)
p=json.loads((ROOT/'protocol/reserved_holdout_v1.json').read_text())
BASE='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a' and dict(attrs).get('href'):self.hrefs.append(dict(attrs)['href'])
def read(day,identity):
    url=BASE+day+'/'+identity+'/'
    try:
        with build_opener(ProxyHandler({})).open(Request(url,headers={'User-Agent':'cattle-research-metadata/1.0'}),timeout=25) as response:data=response.read(2*1024*1024)
    except HTTPError as e:
        if e.code!=404:raise
        return (day,identity),{'url':url,'camera1_files':[],'missing_directory':True}
    path=OUT/f'{day}_{identity}.html';path.write_bytes(data);parser=Links();parser.feed(data.decode('utf-8'))
    images=sorted({urljoin(url,h) for h in parser.hrefs if urlsplit(h).path.endswith('_1.jpg')})
    assert all(h.startswith(url) for h in images)
    return (day,identity),{'url':url,'camera1_files':images,'html_sha256':hashlib.sha256(data).hexdigest(),'missing_directory':False}
directories={}
with ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(read,day,identity) for identity in p['ranked_candidates'] for day in ['2023Aug14','2023Aug20']]
    for future in as_completed(futures):key,result=future.result();directories[key]=result
eligible=[];excluded=[]
for identity in p['ranked_candidates']:
    counts={day:len(directories[(day,identity)]['camera1_files']) for day in ['2023Aug14','2023Aug20']}
    if min(counts.values())>=5:eligible.append(identity)
    else:excluded.append({'identity':identity,'camera1_counts':counts,'reason':'Fewer than5 images on required date; source metadata only'})
assert len(eligible)>=12,(eligible,excluded)
roles={'registered_ids':eligible[:6],'unknown_ids':eligible[6:12],'unused_reserve':eligible[12:]}
sources=[]
for role,ids in roles.items():
    if role=='unused_reserve':continue
    for identity in ids:
        for day in (['2023Aug14','2023Aug20'] if role=='registered_ids' else ['2023Aug20']):
            files=directories[(day,identity)]['camera1_files'];indices=[round(i*(len(files)-1)/4) for i in range(5)]
            for i in indices:sources.append({'role':role,'identity':identity,'day':day,'camera':1,'source_url':files[i],'sequence_index':i,'sequence_length':len(files)})
record={'status':'ELIGIBLE_FUTURE_HOLDOUT_METADATA_ONLY','roles':roles,'excluded':excluded,'image_entries':sources,
        'protocol_sha256':hashlib.sha256((ROOT/'protocol/reserved_holdout_v1.json').read_bytes()).hexdigest(),
        'image_bytes_downloaded':0,'identity_inference_performed':False,'future_read_gate':'Model/method/threshold choice frozen on existing training/validation before images are released to inference'}
(OUT/'eligibility.json').write_text(json.dumps(record,indent=2));print(json.dumps({'status':record['status'],'roles':roles,'excluded':excluded,'planned_images':len(sources),'image_bytes_downloaded':0}),flush=True)
