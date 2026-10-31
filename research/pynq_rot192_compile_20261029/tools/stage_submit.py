from pathlib import Path
import json, hashlib, tarfile, subprocess, sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
files=[p for p in (ROOT/'compiler_workspace').rglob('*') if p.is_file()]
files += [ROOT/p for p in ['protocol/compile_v1.json','tools/compile_rot192.py','tools/normalize_graph.py','tools/compile.slurm']]
archive=ROOT/'compile_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in sorted(files):tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
(ROOT/'evidence/compile_input_transfer.json').write_text(json.dumps({'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files)},indent=2)+'\n')
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/'+ROOT.name+'_inputs.tar.gz'],check=True)
script='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
id -un
hostname
printf '%s\n' "$HOME"
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
project=Path('REMOTE');root=project/'PHASE';archive=project/'PHASE_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
live=subprocess.check_output(['sinfo','-h','-p','cu','-o','%a'],text=True)
assert 'up' in live.split()
assert not root.exists();root.mkdir();(root/'logs').mkdir();(root/'results').mkdir()
with tarfile.open(archive) as tar:
 for item in tar.getmembers():
  assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
p=json.loads((root/'protocol/compile_v1.json').read_text())
for row in p['workspace_files']:assert hashlib.sha256((root/'compiler_workspace'/row['relative_file']).read_bytes()).hexdigest()==row['sha256']
for key,relative in [('compile_script_sha256','tools/compile_rot192.py'),('normalization_script_sha256','tools/normalize_graph.py')]:assert hashlib.sha256((root/relative).read_bytes()).hexdigest()==p[key]
assert hashlib.sha256(Path(p['source_checkpoint']).read_bytes()).hexdigest()==p['source_checkpoint_sha256']
print('FROZEN_NEW_ROT192_COW_MODEL_AND60_VERIFIED_COMPILER_FILES_STAGED')
PY
sbatch --parsable PHASE/tools/compile.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('DIGEST',sha(archive))
file=ROOT/'tools/submit_generated.sh';assert not file.exists();file.write_text(script,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/submit.txt')],check=True)
