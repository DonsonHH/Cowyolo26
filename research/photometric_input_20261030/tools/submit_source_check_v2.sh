set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130613,130614,130615 --format=JobID,State,ExitCode,Elapsed -P
cd /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,subprocess
assert subprocess.check_output(['sacct','-j','130614','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('FAILED|1:0')
a=Path('source_check_inputs_v2.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='979128eef5b8af6a68213012f99e3f5b72f157f214df7a7cc68bafe027cb9cc0'
with tarfile.open(a) as t:
 for m in t.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(t.extractfile(m).read())
print('SHA_HELPER_ACCEPTS_STR_AND_PATH_LOCALLY;NO_NETWORK_RERUN')
PY
sbatch --parsable tools/source_check_v2.slurm
