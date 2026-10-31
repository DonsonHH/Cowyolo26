from pathlib import Path
from urllib.request import build_opener,ProxyHandler,Request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import re,json
OUT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2/catalog')
urls=[
 'https://data.mendeley.com/public-api/datasets/dk54zg67dd/files?folder_id=root&version=1',
 'https://data.mendeley.com/public-api/datasets/dk54zg67dd/files?version=1',
 'https://data.mendeley.com/public-api/datasets/dk54zg67dd/folders?version=1',
 'https://data.mendeley.com/api/datasets-v2/datasets/dk54zg67dd/files?version=1',
 'https://data.mendeley.com/public-api/datasets/dk54zg67dd/1/files'
]
def f(item):
 i,u=item
 try:
  op=build_opener(ProxyHandler({}))
  with op.open(Request(u,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json'}),timeout=15) as r:d=r.read(4*1024*1024)
  (OUT/f'mendeley_endpoint_{i}.txt').write_bytes(d)
  return {'i':i,'url':u,'bytes':len(d),'preview':d.decode()[:3500]}
 except Exception as e:return {'i':i,'url':u,'error':str(e)[:140]}
with ThreadPoolExecutor(max_workers=3) as p:rows=list(p.map(f,enumerate(urls)))
for r in rows:print(json.dumps(r),flush=True)
html=(OUT/'mendeley_page.txt').read_text();scripts=re.findall(r'<script[^>]+src="([^"]+)"',html)
print('PAGE_SCRIPTS',json.dumps(scripts))
(OUT/'mendeley_endpoint_results.json').write_text(json.dumps(rows,indent=2))
