from pathlib import Path
import hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
files=[ROOT/r for r in ['tools/export_encoder_v2.py','tools/export_v2.slurm','protocol/execution_v2.json']]
archive=ROOT/'resume_inputs.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for p in files:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
digest=hashlib.sha256(archive.read_bytes()).hexdigest();bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/'+ROOT.name+'_resume_inputs.tar.gz'],check=True)
script='''set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130569 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,subprocess
root=Path('PHASE');archive=Path('PHASE_resume_inputs.tar.gz')
state=subprocess.check_output(['sacct','-j','130569','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('FAILED|1:0')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
for name in ['encoder.pt','encoder.ncnn.param','encoder.ncnn.bin']:assert (root/'results/export'/name).is_file()
assert not (root/'results/export_v2').exists()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
print('FAILED_WRAPPER_AND_CONVERTED_ASSETS_PRESERVED;NO_REEXPORT_OR_TRAINING')
PY
sbatch --parsable PHASE/tools/export_v2.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('DIGEST',digest)
file=ROOT/'tools/submit_resume_generated.sh';assert not file.exists();file.write_text(script,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(file),'--output',str(ROOT/'evidence/resume_submit.txt')],check=True)
