set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
from urllib.request import Request,urlopen
import json,concurrent.futures,time
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
members=json.loads((root/'results/archive_weight_members.json').read_text())['members']
def inspect(row):
    url='https://data.bris.ac.uk/datasets/'+row['name'];started=time.perf_counter()
    try:
        with urlopen(Request(url,method='HEAD',headers={'User-Agent':'CattleResearch-author-weight-metadata/1.0'}),timeout=20) as response:
            length=int(response.headers['Content-Length'])
            return {'url':url,'HTTP':response.status,'bytes':length,
                    'size_matches_archive_member':length==row['uncompressed_size'],
                    'ETag':response.headers.get('ETag'),'Content-Type':response.headers.get('Content-Type'),
                    'elapsed_s':time.perf_counter()-started,'weight_payload_read':False}
    except Exception as error:
        return {'url':url,'error_type':type(error).__name__,'message':str(error),'weight_payload_read':False}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(inspect,members))
target=root/'results/author_weight_HEAD_checks.json';assert not target.exists()
value={'checks':results,'weight_payload_downloaded_or_loaded':False,'new_model_training_or_forward':False}
target.write_text(json.dumps(value,indent=2));print(json.dumps(value),flush=True)
PY
