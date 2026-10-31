set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
python - <<'PY'
from pathlib import Path
import importlib.util,json,os
root=Path('/share/home/renly/projects/idcoo_research_20261026/env/lib/python3.13/site-packages/ultralytics')
for rel in ['utils/plotting.py','utils/metrics.py','utils/__init__.py','models/yolo/detect/val.py','utils/tal.py']:
 p=root/rel
 print('IMPORTS',rel)
 print('\n'.join(x for x in p.read_text().splitlines()[:100] if x.startswith(('import ','from '))))
print('OTHER_ENV_MATPLOTLIB', [str(p) for p in Path('/share/home/renly/miniconda3/envs').glob('*/lib/python*/site-packages/matplotlib')])
for pid in ['4157790','4159233']:
 p=Path('/proc')/pid/'cmdline'
 if p.exists():print('LIVE_HELPER',pid,p.read_bytes().replace(b'\x00',b' ').decode()[:250])
PY
