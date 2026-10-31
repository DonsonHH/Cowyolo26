set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import hashlib,json,subprocess,os
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
protocol=json.loads((root/'protocol/tail_cache_transport_v1.json').read_text())
script=root/'tools/prefetch_tail_cache.py'
assert hashlib.sha256(script.read_bytes()).hexdigest()==protocol['code_sha256']
assert hashlib.sha256((root/'input/image_fetch_manifest.json').read_bytes()).hexdigest()==protocol['source_fetch_manifest_sha256']
compile(script.read_text(),str(script),'exec')
assert not (root/'results/tail_cache_01').exists()
primary=Path('/proc/2794954');assert primary.exists() and primary.stat().st_uid==os.getuid()
cmd=(primary/'cmdline').read_bytes().replace(b'\0',b' ').decode()
assert str(root/'tools/fetch_images.py') in cmd and '--attempt 01' in cmd
args=[str(root.parent/'env/bin/python'),'-u',str(script)]
with (root/'logs/tail-cache-01.log').open('xb') as log:
    child=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,cwd=root,start_new_session=True)
record={'PID':child.pid,'command':args,'code_sha256':protocol['code_sha256'],'primary_PID':2794954,
        'primary_restarted':False,'source_items':300,'cache_workers':3,
        'maximum_combined_workers':9,'new_model_forward_or_training':False}
(root/'results/tail_cache_launch_01.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record),flush=True)
PY
