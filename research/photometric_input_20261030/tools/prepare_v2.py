"""Keep failed output untouched; repair only JSON-key comparison semantics."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,subprocess,sys,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
old=(ROOT/'tools/run_study.py').read_text(encoding='utf-8')
text=old.replace("protocol/study_v1.json","protocol/study_v2.json").replace("protocol/execution_v1.json","protocol/execution_v2.json").replace("ROOT/'results/study'","ROOT/'results/study_v2'")
before="if condition=='none':assert trace==gz(prior/video['name']/mode/('stride'+str(stride)+'_counter_trace.json.gz'))"
after="if condition=='none':assert json.loads(json.dumps(trace))==gz(prior/video['name']/mode/('stride'+str(stride)+'_counter_trace.json.gz'))"
assert text.count(before)==1;text=text.replace(before,after)
script=ROOT/'tools/run_study_v2.py';assert not script.exists();script.write_text(text,encoding='utf-8',newline='\n');ast.parse(text)
p=json.loads((ROOT/'protocol/study_v1.json').read_text(encoding='utf-8'))
p.update({'status':'FROZEN_JSON_KEY_COMPARISON_REPAIR_BEFORE_V2_FORWARDS','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'original_failed_job':'130611','no_network_probe_job':'130612','repair':'JSON_roundtrip_trace_before_full_comparison_int_keys_to_strings_only',
    'failed_outputs_retained_remote':'results/study','new_outputs':'results/study_v2','expected_prior_failed_forwards':7492,
    'all_conditions_and_numeric_thresholds_unchanged':True})
save(ROOT/'protocol/study_v2.json',p)
slurmtext=(ROOT/'tools/run.slurm').read_text(encoding='utf-8').replace('study-%j','study-v2-%j').replace('tools/run_study.py','tools/run_study_v2.py')
slurm=ROOT/'tools/run_v2.slurm';assert not slurm.exists();slurm.write_text(slurmtext,encoding='utf-8',newline='\n')
files=[script,ROOT/'tools/photometric.py',slurm,*sorted((ROOT/'input').glob('*'))]
save(ROOT/'protocol/execution_v2.json',{'protocol_sha256':sha(ROOT/'protocol/study_v2.json'),'files_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in files}})
staged=[script,slurm,ROOT/'protocol/study_v2.json',ROOT/'protocol/execution_v2.json']
archive=ROOT/'inputs_v2.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for f in staged:tar.add(f,arcname=f.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(archive),REMOTE+'/'+ROOT.name+'/inputs_v2.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE/PHASE
../env/bin/python - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess
old=subprocess.check_output(['sacct','-j','130611','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
probe=subprocess.check_output(['sacct','-j','130612','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
assert old.startswith('FAILED|1:0') and probe.startswith('COMPLETED|0:0')
p=json.loads(Path('results/baseline_trace_probe.json').read_text())
assert p['status']=='BASELINE_TRACE_FAILURE_IS_JSON_INT_VS_STRING_KEYS_ALL_VALUES_EVENTS_AND_IDS_EXACT'
assert all(r['after_JSON_roundtrip_full_trace_exact'] and not r['direct_equality'] for r in p['records'])
archive=Path('inputs_v2.tar.gz');assert hashlib.sha256(archive.read_bytes()).hexdigest()=='HASH'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.write_bytes(tar.extractfile(m).read())
assert Path('results/study/none/validation_all_raw.npz').exists() and not Path('results/study_v2').exists()
print('JSON_KEY_ONLY_CAUSE_VERIFIED_4350_TICKS;OLD_FAILED_RESULTS_UNCHANGED')
PY
sbatch --parsable tools/run_v2.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(archive))
f=ROOT/'tools/submit_v2.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/submission_v2.txt')],check=True)
