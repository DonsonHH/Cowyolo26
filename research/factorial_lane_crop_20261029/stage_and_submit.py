from pathlib import Path
import tarfile,json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=[p for folder in ['input','protocol','tools'] for p in sorted((ROOT/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
files.extend([ROOT/'run.slurm',ROOT/'prepare_execution.py'])
manifest=ROOT/'staging_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=ROOT/'staging_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in [*files,manifest]:tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
(ROOT/'evidence').mkdir(exist_ok=False)
(ROOT/'evidence/staging_transfer.json').write_text(json.dumps({'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1},indent=2)+'\n')
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/factorial_lane_crop_20261029_inputs.tar.gz'],check=True)
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
project=Path('/share/home/renly/projects/idcoo_research_20261026');archive=project/'factorial_lane_crop_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ARCHIVE_DIGEST'
root=project/'factorial_lane_crop_20261029';root.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for member in tar.getmembers():
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        target=(root/member.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(member).read())
for row in json.loads((root/'staging_manifest.json').read_text()):
    file=root/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
(root/'logs').mkdir(exist_ok=False)
print('ALL15_FROZEN_CHECKPOINT_CROP_INPUTS_STAGED_HASH_EXACT;NO_NEW_TRAINING')
PY
sbatch --parsable factorial_lane_crop_20261029/run.slurm
'''.replace('ARCHIVE_DIGEST',sha(archive))
script=ROOT/'submit_generated.sh';assert not script.exists();script.write_text(text,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/submit.txt')],check=True)
