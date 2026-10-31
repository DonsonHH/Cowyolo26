set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
from collections import Counter
import hashlib,json,os
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
summary=json.loads((root/'results/download_attempt_01/summary.json').read_text())
errors=json.loads((root/'results/download_attempt_01/errors.json').read_text())
manifest_path=root/'results/download_attempt_01/image_manifest.json'
manifest=json.loads(manifest_path.read_text())
assert summary['status']=='PARTIAL_IMAGE_TRANSFER_FAILURE' and summary['saved_images']==len(manifest)==8369
assert summary['failed_images']==len(errors)==11
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==summary['image_manifest_sha256']
current=None
try:current=Path('/proc/2794954/cmdline').read_bytes().replace(b'\0',b' ').decode()
except FileNotFoundError:pass
assert current is None or str(root/'tools/fetch_images.py') not in current
cache=json.loads((root/'results/tail_cache_01/summary.json').read_text())
cache_manifest=root/'results/tail_cache_01/member_manifest.json'
assert cache['failed_members']==0 and hashlib.sha256(cache_manifest.read_bytes()).hexdigest()==cache['member_manifest_sha256']
value={'transfer_summary':summary,'native_original_command':current,
       'failed_names':[r['file_name'] for r in errors],'error_types':dict(Counter(r['error']['type'] for r in errors)),
       'first_error':errors[0], 'tail_cache_summary':cache,
       'handoff_terminal':json.loads((root/'results/download_handoff_01/summary.json').read_text()) if (root/'results/download_handoff_01/summary.json').exists() else None}
print(json.dumps(value),flush=True)
PY
