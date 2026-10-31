set -euo pipefail
PROJECT=/share/home/renly/projects/idcoo_research_20261026
"$PROJECT/env/bin/python" - <<'PY'
from pathlib import Path
import json
p=Path('/share/home/renly/projects/idcoo_research_20261026')
discovery=json.loads((p/'catalog/discovery.json').read_text())
row=next(r for r in discovery if r['name'].endswith('_Videos'))
links=[u for u in row.get('links',[]) if '/Identification/Videos/2020-' in u and u.endswith('/')]
existing=[]
for v in sorted((p/'data/cows2021_samples').glob('*/RGB.avi')):
    existing.append({'sequence':v.parent.name,'bytes':v.stat().st_size,'manifest_exists':v.with_suffix('.avi.manifest.json').exists()})
value={'status':'COWS_VIDEO_INDEX_AND_EXISTING_FILES_READ','directory_URL':row['url'],'published_video_directory_links':links,
       'existing_local_server_samples':existing,'discovery_rows':len(discovery)}
print(json.dumps(value))
PY
