set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/cows2021_adaptation_20261027"
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import requests,time,json,socket
stage=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
items=json.loads((stage/'input/image_fetch_manifest.json').read_text())['items']
files=list((stage/'raw_images').rglob('*.jpg'))
sizes=[p.stat().st_size for p in files]
print(json.dumps({'downloaded_files':len(files),'bytes':sum(sizes),'mean_image_bytes':sum(sizes)/max(1,len(sizes))}))
session=requests.Session();session.trust_env=False
row=items[0];start=time.perf_counter()
with session.get(row['url'],timeout=(10,30),stream=True) as response:
    response.raise_for_status();headers_at=time.perf_counter();body=response.content
print(json.dumps({'benchmark_file':row['file_name'],'HTTP':response.status_code,'bytes':len(body),
                  'headers_s':headers_at-start,'total_s':time.perf_counter()-start,'connection':response.headers.get('Connection')}))
PY
