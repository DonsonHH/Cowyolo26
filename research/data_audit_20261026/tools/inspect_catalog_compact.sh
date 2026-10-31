python - <<'PY'
import json,urllib.request,html.parser
from pathlib import Path
root=Path('/share/home/renly/projects/idcoo_research_20261026')
rows=json.loads((root/'catalog/discovery.json').read_text())
class L(html.parser.HTMLParser):
 def __init__(self):super().__init__();self.u=[]
 def handle_starttag(self,t,a):
  if t=='a':self.u.extend(v for k,v in a if k=='href')
for r in rows:
 if r['name'].endswith('_Videos'):
  seqs=[u for u in r['links'] if u.startswith(r['url']) and u.endswith('/')]
  print('cows2021_sequence_directories',len(seqs))
  for u in [seqs[0],seqs[-1]]:
   op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
   with op.open(u,timeout=15) as h:data=h.read()
   p=L();p.feed(data.decode());print(json.dumps({'sequence':u,'entries':len(p.u),'links':p.u[:5]}))
for p in (root/'catalog').glob('camera1_date0.html'):
 print(p.read_text()[:2200])
PY
