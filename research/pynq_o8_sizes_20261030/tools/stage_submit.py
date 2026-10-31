from pathlib import Path
import tarfile,json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=[p for case in ['s256','s320'] for p in sorted((ROOT/case).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
files.extend([ROOT/'protocol/sizes_v1.json',ROOT/'tools/compile.slurm'])
archive=ROOT/'compile_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files:tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
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
import tarfile,json,hashlib
root=Path('PHASE');archive=Path('PHASE_inputs.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST' and not root.exists()
root.mkdir();(root/'logs').mkdir()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
for name in ['s256','s320']:
 p=json.loads((root/name/'protocol/compile_v1.json').read_text());assert hashlib.sha256(Path(p['source_checkpoint']).read_bytes()).hexdigest()==p['source_checkpoint_sha256']
 for row in p['workspace_files']:assert hashlib.sha256((root/name/'compiler_workspace'/row['relative_file']).read_bytes()).hexdigest()==row['sha256']
 (root/name/'results').mkdir();(root/name/'logs').mkdir()
print('TWO_FIXED_COW_SIZES_AND_ALL_O8_COMPILER_FILES_FROZEN')
PY
sbatch --parsable PHASE/tools/compile.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('DIGEST',sha(archive))
file=ROOT/'tools/submit_generated.sh';file.write_text(script,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/submit.txt')],check=True)
