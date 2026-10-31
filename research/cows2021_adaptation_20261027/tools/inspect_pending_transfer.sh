set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
from urllib.request import Request,urlopen
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,time
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
items=json.loads((root/'input/image_fetch_manifest.json').read_text())['items']
present={p.name for p in (root/'raw_images').rglob('*.jpg')}
earlier_missing=[r for r in items if r['file_name']<'06000.jpg' and r['file_name'] not in present]
result={'observed_UTC':datetime.now(timezone.utc).isoformat(),'saved_files':len(present),
        'missing_before_06000':[{'file_name':r['file_name'],'role':r['development_role']} for r in earlier_missing]}
if earlier_missing:
    row=earlier_missing[0];started=time.perf_counter()
    try:
        with urlopen(Request(row['url'],headers={'User-Agent':'CattleResearch-transfer-diagnostic/1.0'}),timeout=30) as response:
            body=response.read(8*1024*1024+1)
            result['bounded_retest']={'file_name':row['file_name'],'HTTP':response.status,'bytes':len(body),
                                     'sha256':hashlib.sha256(body).hexdigest(),'elapsed_s':time.perf_counter()-started,
                                     'saved_into_live_download_directory':False,'image_pixels_decoded':False}
    except Exception as error:
        result['bounded_retest']={'file_name':row['file_name'],'error_type':type(error).__name__,
                                 'message':str(error),'elapsed_s':time.perf_counter()-started}
print(json.dumps(result),flush=True)
PY
