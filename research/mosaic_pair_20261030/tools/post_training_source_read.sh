set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib
root=Path('mosaic_pair_20261030');old=Path('detector_factorial_20261029')
p=json.loads((old/'protocol/training_v4.json').read_text());manifest=old/'input/prepared_manifest.json'
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==p['input_sha256']['prepared_manifest.json']
rows=json.loads(manifest.read_text());assert len(rows)==8380
counts=Counter();changed=[]
for r in rows:
 f=Path(r['label_path']);digest=hashlib.sha256(f.read_bytes()).hexdigest();counts[r['actual_split']]+=1
 if digest!=r['label_sha256']:changed.append({'file_name':r['file_name'],'expected':r['label_sha256'],'actual':digest})
assert counts=={'train':6809,'val':1571}
result={'status':'POST_TRAINING_ALL8380_SOURCE_LABEL_FILES_MATCH_OLD_FROZEN_MANIFEST' if not changed else 'SOURCE_LABEL_CHANGES_DETECTED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
 'label_counts':dict(counts),'changed':changed,'scope':'post_training_bytes_vs_preexisting_manifest;not_invented_perrun_file_watch',
 'validation_pixels_read':0,'final_holdout_files_read':0,'new_model_forwards':0,'whole_goal_complete':False}
f=root/'results/source_labels_post_training_integrity.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert not changed
PY
