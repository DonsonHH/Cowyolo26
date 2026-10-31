from pathlib import Path
import hashlib,tarfile,sys,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
files=[ROOT/r for r in ['protocol/eval_v2.json','protocol/execution_v2.json','tools/evaluate_quality_v2.py','tools/frozen_input.py','tools/run_v2.slurm']]
archive=ROOT/'eval_v2_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files:tar.add(file,arcname=file.relative_to(ROOT).as_posix(),recursive=False)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/'+ROOT.name+'_v2_inputs.tar.gz'],check=True)
script='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130567 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json,subprocess
root=Path('PHASE');archive=Path('PHASE_v2_inputs.tar.gz')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
state=subprocess.check_output(['sacct','-j','130567','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('FAILED|1:0')
assert (root/'results/quality/validation_metrics.json').exists() and not (root/'results/quality_v2').exists()
with tarfile.open(archive) as tar:
 for item in tar.getmembers():
  assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
print('FAILED130567_PRESERVED;ALL8_EXACT_GPU_INPUT_GATES_BEFORE_NEW_FORWARDS')
PY
sbatch --parsable PHASE/tools/run_v2.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('DIGEST',digest)
file=ROOT/'tools/submit_v2_generated.sh';assert not file.exists();file.write_text(script,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/submit_v2.txt')],check=True)
