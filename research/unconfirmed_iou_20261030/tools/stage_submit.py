from pathlib import Path
from datetime import datetime,timezone
import ast,json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
job=f'''#!/bin/bash
#SBATCH --job-name=unconfirmed-stage-IoU
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:10:00
#SBATCH --output={REMOTE}/{ROOT.name}/logs/control-%j.out
#SBATCH --error={REMOTE}/{ROOT.name}/logs/control-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1
cd {REMOTE}/{ROOT.name}
../env/bin/python -B tools/run_control.py
'''
f=ROOT/'tools/control.slurm';assert not f.exists();f.write_text(job,encoding='utf-8',newline='\n')
files=[ROOT/'tools/confirmation_iou.py',ROOT/'tools/run_control.py',f,*sorted(p for p in (ROOT/'input').glob('*') if p.is_file())]
for f in files:
    if f.suffix=='.py':ast.parse(f.read_text(encoding='utf-8'))
p=ROOT/'protocol/execution_v1.json';assert not p.exists();p.write_text(json.dumps({'created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'protocol_sha256':sha(ROOT/'protocol/control_v1.json'),'files_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in files}},indent=2)+'\n',encoding='utf-8')
a=ROOT/'control_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for f in [*files,ROOT/'protocol/control_v1.json',p]:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
check=ROOT/'tools/cluster_read.sh';assert not check.exists();check.write_text('''set -euo pipefail
id -un
hostname
printf '%s\\n' "$HOME"
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
scontrol show partition -o
test ! -e '''+REMOTE+'/'+ROOT.name+'\ntest ! -e '+REMOTE+'/'+ROOT.name+'_control_inputs_v1.tar.gz\n',encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(check),'--output',str(ROOT/'evidence/cluster_read.txt')],check=True)
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'_control_inputs_v1.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json
a=Path('PHASE_control_inputs_v1.tar.gz');root=Path('PHASE');assert not root.exists() and hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
p=json.loads((root/'protocol/control_v1.json').read_text())
for c in p['caches']:
 assert hashlib.sha256(Path(c['raw_file']).read_bytes()).hexdigest()==c['raw_sha256'],c['id']
 assert hashlib.sha256(Path(c['trace_file']).read_bytes()).hexdigest()==c['trace_sha256'],c['id']
print('ALL111_REMOTE_RAW_AND_BASELINE_FILES_EXIST_AND_HASH_MATCH_BEFORE_SUBMISSION')
PY
sbatch --parsable PHASE/tools/control.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/submit_generated.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/submission.txt')],check=True)
