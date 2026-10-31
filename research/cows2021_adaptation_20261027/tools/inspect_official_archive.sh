set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from urllib.request import Request,urlopen
import time,json
url='https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/4vnrca7qw1642qlwxjadp87h7.zip'
started=time.perf_counter()
try:
    with urlopen(Request(url,method='HEAD',headers={'User-Agent':'CattleResearch-archive-metadata-check/1.0'}),timeout=20) as r:
        print(json.dumps({'url':url,'HTTP':r.status,'Content-Length':r.headers.get('Content-Length'),
                          'Accept-Ranges':r.headers.get('Accept-Ranges'),'Content-Type':r.headers.get('Content-Type'),
                          'ETag':r.headers.get('ETag'),'Last-Modified':r.headers.get('Last-Modified'),
                          'elapsed_s':time.perf_counter()-started,'image_payload_read':False}))
except Exception as error:
    print(json.dumps({'URL':url,'error_type':type(error).__name__,'message':str(error),'image_payload_read':False}))
PY
