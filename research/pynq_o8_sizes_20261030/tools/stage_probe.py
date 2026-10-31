from pathlib import Path
import tarfile,subprocess,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
job=f'''#!/bin/bash
#SBATCH --job-name=O8-320-one-vector-probe
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=10G
#SBATCH --time=00:08:00
#SBATCH --output={REMOTE}/{ROOT.name}/logs/probe-%j.out
#SBATCH --error={REMOTE}/{ROOT.name}/logs/probe-%j.err
set -euo pipefail
cd {REMOTE}/{ROOT.name}
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
../env/bin/python -B tools/probe320.py
'''
(ROOT/'tools/probe.slurm').write_text(job,newline='\n')
archive=ROOT/'probe_inputs.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for name in ['tools/probe320.py','tools/probe.slurm']:tar.add(ROOT/name,arcname=name,recursive=False)
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/'+ROOT.name+'_probe_inputs.tar.gz'],check=True)
script='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import tarfile,hashlib
root=Path('PHASE');a=Path('PHASE_probe_inputs.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='DIGEST'
assert (root/'s320/results/qualification/parity_train_4.npz').exists() and not (root/'results/probe320').exists()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
PY
sbatch --parsable PHASE/tools/probe.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('DIGEST',hashlib.sha256(archive.read_bytes()).hexdigest())
file=ROOT/'tools/submit_probe.sh';file.write_text(script,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/probe_submit.txt')],check=True)
