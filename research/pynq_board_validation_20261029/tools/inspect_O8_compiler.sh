set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib
root=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8')
chosen=['recompile_release.py','regenerate_release.py','recompile_native.py','selected_candidates.json','requirements_pc.txt']
for folder in ['compiler','tools']:
    for f in sorted((root/folder).glob('*.py')):
        if any(word in f.name.lower() for word in ['compile','export','quant','resident','plan','convert','pack','graph']):chosen.append(f.relative_to(root).as_posix())
rows=[]
for relative in chosen:
    path=root/relative
    if not path.is_file():rows.append({'relative':relative,'exists':False});continue
    b=path.read_bytes();rows.append({'relative':relative,'exists':True,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'text':b.decode('utf-8','replace') if len(b)<80000 else None})
programs=[]
for folder in sorted(root.glob('program_r*')):
    p=folder/'program.json'
    if p.is_file():
        o=json.loads(p.read_text());programs.append({'relative':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'keys':list(o),'nodes':len(o.get('nodes',[])),'bytes':p.stat().st_size})
print(json.dumps({'status':'READONLY_O8_COMPILATION_ENTRYPOINTS','sources':rows,'available_programs':programs,'hardware_actions':0,'model_forwards':0}))
PY
