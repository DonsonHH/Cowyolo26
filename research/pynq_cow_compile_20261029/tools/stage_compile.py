from pathlib import Path
import json,hashlib,tarfile,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[p for folder in ['compiler_workspace','protocol','tools'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest=ROOT/'staging_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'relative_file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=ROOT/'compile_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for p in [*files,manifest]:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
record={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1}
(ROOT/'evidence/input_transfer.json').write_text(json.dumps(record,indent=2)+'\n')
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/pynq_cow_compile_20261029_inputs.tar.gz'],check=True)
text='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
command -v g++
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,importlib.util
root=Path('/share/home/renly/projects/idcoo_research_20261026');archive=root/'pynq_cow_compile_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
out=root/'pynq_cow_compile_20261029';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        target=(out/item.name).resolve();assert target.is_relative_to(out.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
for row in json.loads((out/'staging_manifest.json').read_text()):
    p=out/row['relative_file'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
for module in ['torch','onnx','onnxruntime','onnxslim','cv2']:assert importlib.util.find_spec(module),module
(out/'logs').mkdir(exist_ok=False)
print('SOURCE_SNAPSHOT_HASHES_EXACT_CPU_ONLY_COMPILATION_GATE;NO_BOARD_ACTION')
PY
sbatch --parsable pynq_cow_compile_20261029/tools/compile.slurm
'''.replace('DIGEST',sha(archive))
file=ROOT/'tools/submit_compile_generated.sh';assert not file.exists();file.write_text(text,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/compile_submit.txt')],check=True)
