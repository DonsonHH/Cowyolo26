set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
python - <<'PY'
from pathlib import Path
import os,json,hashlib,sys,importlib.metadata as m
root=Path('/share/home/renly/projects/idcoo_research_20261026');rows=[]
for p in sorted((root/'data').rglob('*')):
 if not p.is_file() or p.is_symlink() or not (p.suffix.lower() in ('.avi','.mp4','.zip') or p.name.endswith('.manifest.json') or p.name=='summary.json'):continue
 rows.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size})
version={}
for n in ('ultralytics','torch','torchvision','opencv-python','numpy','pillow','scipy','lap','polars'):
 try:version[n]=m.version(n)
 except m.PackageNotFoundError:version[n]=None
out={'files':rows,'python':sys.version,'runtime_packages':version,'login_host':os.uname().nodename,'project_root':str(root),'all_computation_scope':'Slurm jobs; login node only transfer/setup/metadata'}
(root/'results/server_inventory.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
PY
