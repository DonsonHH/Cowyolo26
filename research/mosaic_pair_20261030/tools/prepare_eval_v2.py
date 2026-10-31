from pathlib import Path
from datetime import datetime,timezone
import ast,json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
probe=load(ROOT/'results/regression_diagnostic.json');assert len(probe['rows'])==9 and probe['new_network_forwards']==0
for r in probe['rows']:
    assert r['difference_counts']=={'structure':1} and r['maximum_errors']=={} and r['confirmed_events_exact'] and r['handoff_events_exact']
    d=r['first12_differences'];assert len(d)==1 and d[0]['kind']=='dict_keys'
    assert set(d[0]['expected'])-set(d[0]['actual'])=={'effective_tracker_config'}
text=(ROOT/'tools/evaluate.py').read_text(encoding='utf-8')
text=text.replace('protocol/evaluation_v1.json','protocol/evaluation_v2.json').replace('protocol/evaluation_execution_v1.json','protocol/evaluation_execution_v2.json')
text=text.replace("ROOT/'results/evaluation'","ROOT/'results/evaluation_v2'").replace("ROOT/'results/evaluation_manifest.json'","ROOT/'results/evaluation_manifest_v2.json'")
needle="{'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}"
assert text.count(needle)==2
text=text.replace(needle,"{'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[],'effective_tracker_config':p['tracker_config']}")
start=text.index("    save_new(ROOT/'results/all_six_checkpoints_frozen.json',")
end=text.index('    port=PROJECT/',start)
text=text[:start]+'''    joint=ROOT/'results/all_six_checkpoints_frozen.json'
    assert sha(joint)==p['original_joint_freeze_sha256']
    original_freeze=load(joint)
    assert original_freeze['models']==frozen and original_freeze['source_image_forwards_at_freeze']==0
'''+text[end:]
script=ROOT/'tools/evaluate_v2.py';assert not script.exists();script.write_text(text,encoding='utf-8',newline='\n');ast.parse(text)
p=load(ROOT/'protocol/evaluation_v1.json');p.update({'status':'FROZEN_MISSING_EFFECTIVE_CONFIG_METADATA_REPAIR_BEFORE_ANY_NEW_MODEL_SOURCE_FORWARD',
    'created_host_UTC':datetime.now(timezone.utc).isoformat(),'original_failed_job':'130628','original_failed_source_image_forwards':0,
    'diagnostic_job':'130629','metadata_key_added':'effective_tracker_config','all_numeric_trace_values_IDs_events_already_exact':True,
    'strict_trace_equality_retained':True,'numeric_confidence_ROI_or_counter_gate_changed':False,
    'original_joint_freeze_sha256':sha(ROOT/'results/all_six_checkpoints_frozen.json'),'original_weights_manifest_reused_without_retraining':True})
save(ROOT/'protocol/evaluation_v2.json',p)
slurmtext=(ROOT/'tools/evaluate.slurm').read_text(encoding='utf-8').replace('evaluation-%j','evaluation-v2-%j').replace('tools/evaluate.py','tools/evaluate_v2.py')
slurm=ROOT/'tools/evaluate_v2.slurm';assert not slurm.exists();slurm.write_text(slurmtext,encoding='utf-8',newline='\n')
files=[script,slurm,*sorted((ROOT/'input').glob('*')),ROOT/'tools/common.py']
save(ROOT/'protocol/evaluation_execution_v2.json',{'protocol_sha256':sha(ROOT/'protocol/evaluation_v2.json'),'files_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in files}})
staged=[script,slurm,ROOT/'protocol/evaluation_v2.json',ROOT/'protocol/evaluation_execution_v2.json']
a=ROOT/'evaluation_inputs_v2.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for f in staged:tar.add(f,arcname=f.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'/evaluation_inputs_v2.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE/PHASE
../env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
assert subprocess.check_output(['sacct','-j','130628','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('FAILED|1:0')
assert subprocess.check_output(['sacct','-j','130629','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('COMPLETED|0:0')
assert hashlib.sha256(Path('results/all_six_checkpoints_frozen.json').read_bytes()).hexdigest()=='FREEZE'
assert not list(Path('results/evaluation').rglob('*')) and not Path('results/evaluation_v2').exists()
a=Path('evaluation_inputs_v2.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
print('STRICT_EQUALITY_RETAINED;ONLY_MISSING_METADATA_KEY_REPAIRED;SIX_WEIGHTS_UNCHANGED')
PY
sbatch --parsable tools/evaluate_v2.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('FREEZE',sha(ROOT/'results/all_six_checkpoints_frozen.json')).replace('HASH',sha(a))
f=ROOT/'tools/submit_evaluation_v2.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/evaluation_submission_v2.txt')],check=True)
