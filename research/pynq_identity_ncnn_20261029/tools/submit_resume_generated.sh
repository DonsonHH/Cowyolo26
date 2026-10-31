set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sacct -j 130569 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,subprocess
root=Path('pynq_identity_ncnn_20261029');archive=Path('pynq_identity_ncnn_20261029_resume_inputs.tar.gz')
state=subprocess.check_output(['sacct','-j','130569','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('FAILED|1:0')
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='b5ac2a1febf46d1d92c6c6a76dcb892e22ed9f4cbd568758ffe690b955294b98'
for name in ['encoder.pt','encoder.ncnn.param','encoder.ncnn.bin']:assert (root/'results/export'/name).is_file()
assert not (root/'results/export_v2').exists()
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  p=(root/m.name).resolve();assert p.is_relative_to(root.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(m).read())
print('FAILED_WRAPPER_AND_CONVERTED_ASSETS_PRESERVED;NO_REEXPORT_OR_TRAINING')
PY
sbatch --parsable pynq_identity_ncnn_20261029/tools/export_v2.slurm
