from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urljoin
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
BASE='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            value=dict(attrs).get('href')
            if value:self.hrefs.append(value)
def fetch(item):
    name,url=item;record={'name':name,'requested_url':url,'started_UTC':datetime.now(timezone.utc).isoformat()}
    try:
        opener=build_opener(ProxyHandler({}))
        with opener.open(Request(url,headers={'User-Agent':'cow-source-provenance-audit/1.0','Accept':'application/json' if 'api.github.com' in url else '*/*'}),timeout=40) as response:
            data=response.read(5*1024*1024+1);assert len(data)<=5*1024*1024
            record.update(final_url=response.url,status=response.status,content_type=response.headers.get('Content-Type'),
                          last_modified=response.headers.get('Last-Modified'),etag=response.headers.get('ETag'))
        path=ROOT/'evidence/primary'/name;assert not path.exists();path.write_bytes(data)
        record.update(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),file=path.relative_to(ROOT).as_posix())
        if 'text/html' in (record['content_type'] or ''):
            parser=Links();parser.feed(data.decode('utf-8'));record['links']=[urljoin(url,h) for h in parser.hrefs]
    except Exception as error:record.update(error_type=type(error).__name__,error=str(error)[:250])
    return record
def main():
    (ROOT/'evidence/primary').mkdir(parents=True,exist_ok=False)
    urls=[('dataset_root.html',BASE),('dataset_readme.txt',BASE+'readme.txt'),
          ('image_root.html',BASE+'MultiCamCows2024Root/'),('day14.html',BASE+'MultiCamCows2024Root/2023Aug14/'),
          ('videos_root.html',BASE+'MultiCamCows2024Root/videos/'),
          ('author_repo_commit.json','https://api.github.com/repos/Phoenix4582/CowIDentifier/commits/main'),
          ('author_repo_tree.json','https://api.github.com/repos/Phoenix4582/CowIDentifier/git/trees/main?recursive=1'),
          ('author_public_repos.json','https://api.github.com/users/Phoenix4582/repos?per_page=100&type=owner'),
          ('author_project.html','https://phoenix4582.github.io/MultiCamCows2024.github.io/'),
          ('author_paper.html','https://pmc.ncbi.nlm.nih.gov/articles/PMC7619405/'),
          ('author_appendix.pdf','https://pmc.ncbi.nlm.nih.gov/articles/instance/7619405/bin/EMS217219-supplement-Appendix.pdf')]
    urls += [(f'day14_ID{identity}.html',BASE+f'MultiCamCows2024Root/2023Aug14/{identity}/') for identity in ['009','020','026','028','031','054']]
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(fetch,urls))
    out=ROOT/'evidence/primary_manifest.json';assert not out.exists();out.write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    for record in records:print(json.dumps({k:v for k,v in record.items() if k not in ['links','etag','last_modified']}),flush=True)
if __name__=='__main__':main()
