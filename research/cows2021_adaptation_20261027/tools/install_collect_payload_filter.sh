set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
"$project/env/bin/python" - <<'PY'
from pathlib import Path
import json,hashlib,shutil
root=Path('/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027')
original=root/'tools/collect.py'
new=root/'tools/collect_without_transport_payloads.py'
expected={r['path']:r for r in json.loads((root/'results/replay_and_sample_tools_v1.json').read_text())}
assert hashlib.sha256(original.read_bytes()).hexdigest()==expected['tools/collect.py']['sha256']
old_text=original.read_text();new_text=new.read_text()
added="            if 'JPEGs' in path.parts or path.name.endswith('.partial'):continue\n"
assert new_text.replace(added,'')==old_text
assert not (root/'results/inference').exists() and not (root/'delivery.tar.gz').exists()
backup=root/'tools/history/collect_before_transport_payload_filter.py'
assert not backup.exists();shutil.copyfile(original,backup)
compile(new_text,str(original),'exec');shutil.copyfile(new,original)
result={'status':'COLLECTION_FILTER_UPDATED_BEFORE_MODEL_EXECUTION','old_script_sha256':expected['tools/collect.py']['sha256'],
        'new_script_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
        'change':'exclude transport cache JPEG directories and partial files from reproducibility archive',
        'source_images_or_results_removed':False,'training_or_replay_started':False}
target=root/'results/collection_transport_filter_update.json';assert not target.exists()
target.write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
PY
