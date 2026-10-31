from pathlib import Path
import json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[ROOT/'protocol/media_and_pixel_v1.json',ROOT/'tools/verify_pixels.py',ROOT/'tools/pixel.slurm']
manifest=ROOT/'input/pixel_staging_manifest.json';assert not manifest.exists()
manifest.write_text(json.dumps([{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=ROOT/'pixel_check_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for p in [*files,manifest]:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
digest=sha(archive)
(ROOT/'evidence/pixel_input_transfer.json').write_text(json.dumps({'bytes':archive.stat().st_size,'sha256':digest,'members':4},indent=2)+'\n')
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/lowres_roi_pixel_inputs.tar.gz'],check=True)
script=ROOT/'tools/submit_pixel_generated.sh';assert not script.exists()
script.write_text('''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json,subprocess
project=Path('/share/home/renly/projects/idcoo_research_20261026');root=project/'lowres_roi_20261029'
state=subprocess.check_output(['sacct','-j','130506','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
assert state.startswith('COMPLETED|0:0'),state
archive=project/'lowres_roi_pixel_inputs.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
for row in json.loads((root/'input/pixel_staging_manifest.json').read_text()):
    p=root/row['file'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
print('PIXEL_INPUTS_EXACT; CPU-only allocation on idle4gpu; cu all allocated in live topology; no GPU GRES requested')
PY
sbatch --parsable lowres_roi_20261029/tools/pixel.slurm
'''.replace('DIGEST',digest),newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/submit_pixel.txt')],check=True)
