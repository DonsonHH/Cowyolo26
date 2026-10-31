set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import ast,hashlib
base=Path('env/lib/python3.13/site-packages/ultralytics')
specs={'data/build.py':['build_yolo_dataset','build_dataloader','seed_worker'],
 'models/yolo/detect/train.py':['build_dataset','get_dataloader','preprocess_batch'],
 'engine/trainer.py':['_setup_train']}
for name,functions in specs.items():
 p=base/name;s=p.read_text();print('FILE',name,'SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
 lines=s.splitlines()
 for node in ast.walk(ast.parse(s)):
  if isinstance(node,ast.FunctionDef) and node.name in functions:
   block='\n'.join(lines[node.lineno-1:node.end_lineno])
   if node.name=='_setup_train':
    for i,line in enumerate(lines[node.lineno-1:node.end_lineno]):
     if any(word in line for word in ['seed','build_dataset','get_dataloader','batch_size','train_loader','test_loader']):print(i+node.lineno,line)
   else:print(block)
 if name=='engine/trainer.py':
  for i,line in enumerate(lines):
   if 'init_seeds' in line or 'RANK =' in line:print(i+1,line)
PY
