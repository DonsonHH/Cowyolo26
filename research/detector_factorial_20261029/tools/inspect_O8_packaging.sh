set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/home/xilinx/jupyter_notebooks');report={}
for project in ['yolo26_optimization_8','yolo26_optimization_7','yolo26_optimization_6']:
    directory=root/project
    dirs=[{'name':p.name,'is_dir':p.is_dir()} for p in sorted(directory.iterdir())] if directory.is_dir() else []
    candidates=[]
    for folder in ['compiler','compiler_sources','tools']:
        candidates.extend({'relative':p.relative_to(directory).as_posix(),'bytes':p.stat().st_size} for p in sorted((directory/folder).glob('*.py')))
    report[project]={'root_items':dirs,'compiler_sources':candidates}
print(json.dumps({'status':'READONLY_RUNTIME_PACKAGING_INVENTORY','projects':report,'model_or_hardware_actions':0}))
PY
