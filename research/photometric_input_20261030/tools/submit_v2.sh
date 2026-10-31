set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd /share/home/renly/projects/idcoo_research_20261026/photometric_input_20261030
../env/bin/python - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess
old=subprocess.check_output(['sacct','-j','130611','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
probe=subprocess.check_output(['sacct','-j','130612','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
assert old.startswith('FAILED|1:0') and probe.startswith('COMPLETED|0:0')
p=json.loads(Path('results/baseline_trace_probe.json').read_text())
assert p['status']=='BASELINE_TRACE_FAILURE_IS_JSON_INT_VS_STRING_KEYS_ALL_VALUES_EVENTS_AND_IDS_EXACT'
assert all(r['after_JSON_roundtrip_full_trace_exact'] and not r['direct_equality'] for r in p['records'])
archive=Path('inputs_v2.tar.gz');assert hashlib.sha256(archive.read_bytes()).hexdigest()=='2664e7993fd5760f105b4dac7da20de3078863679e279055ceee4e838ab8e664'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert Path('results/study/none/validation_all_raw.npz').exists() and not Path('results/study_v2').exists()
print('JSON_KEY_ONLY_CAUSE_VERIFIED_4350_TICKS;OLD_FAILED_RESULTS_UNCHANGED')
PY
sbatch --parsable tools/run_v2.slurm
