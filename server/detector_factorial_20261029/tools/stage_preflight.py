from pathlib import Path
import hashlib,tarfile,json,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[f for folder in ['input','protocol','tools'] for f in sorted((ROOT/folder).rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
manifest=ROOT/'staging_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=ROOT/'preflight_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in [*files,manifest]:tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
record={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1}
(ROOT/'evidence/preflight_input_transfer.json').write_text(json.dumps(record,indent=2)+'\n')
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/detector_factorial_20261029_inputs.tar.gz'],check=True)
script=ROOT/'tools/submit_preflight_generated.sh';assert not script.exists()
text='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026');archive=root/'detector_factorial_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
out=root/'detector_factorial_20261029';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(out/member.name).resolve();assert file.is_relative_to(out.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
for r in json.loads((out/'staging_manifest.json').read_text()):
    f=out/r['file'];assert f.stat().st_size==r['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==r['sha256']
(out/'results').mkdir(exist_ok=False);(out/'logs').mkdir(exist_ok=False)
print('PREFLIGHT_INPUTS_EXACT_NO_FORMAL_TRAINING_SUBMITTED')
PY
sbatch --parsable detector_factorial_20261029/tools/preflight_v2.slurm
'''.replace('DIGEST',sha(archive))
script.write_text(text,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/preflight_submit.txt')],check=True)
