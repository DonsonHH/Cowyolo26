from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
old=ROOT/'tools/run_control.py';text=old.read_text(encoding='utf-8')
insert='''
def replay_hardware_group(group,p,cls):
    assert len(group)==2 and [c['stride'] for c in group]==[6,1]
    assert all(c['board_reference'] and c['scene']=='toros' for c in group)
    pipeline_module.BYTETracker=cls
    pipes={c['id']:pipeline_module.FramePipeline(c['spec'],p['tracker_config'],p['counter_kwargs']) for c in group}
    traces={c['id']:{'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]} for c in group}
    raw={r['frame0']:r['predictions'] for r in gz(group[0]['raw_file'])}
    for pipe in pipes.values():pipe.tracker.focus_frames=[];pipe.tracker.stage_log=[]
    for frame in range(group[0]['spec']['decode_end_exclusive']):
        for c in group:
            if frame%c['stride']:continue
            pipe=pipes[c['id']];pipe.tracker.source_frame0=frame
            value=pipe.update(frame,raw[frame]);traces[c['id']]['observations'].append(value['observation'])
            for key in ['post_tracker','confirmed_only_events','handoff_events']:traces[c['id']][key].extend(value[key])
            assert pipe.tracker.args.fuse_score==p['tracker_config']['fuse_score']
    return {name:(trace,[]) for name,trace in traces.items()}

def scheduled_replay(c,p,cls,completed):
    if c['id'] in completed:return completed[c['id']]
    if c['board_reference'] and c['scene']=='toros':
        group=[r for r in p['caches'] if r['board_reference'] and r['scene']=='toros' and r['label']==c['label']]
        group.sort(key=lambda r:-r['stride'])
        completed.update(replay_hardware_group(group,p,cls))
    else:completed[c['id']]=replay(c,p,cls)
    return completed[c['id']]
'''
assert text.count('def scores(c,trace,variant):')==1;text=text.replace('def scores(c,trace,variant):',insert+'\ndef scores(c,trace,variant):')
text=text.replace('protocol/control_v1.json','protocol/control_v2.json').replace('protocol/execution_v1.json','protocol/execution_v2.json')
text=text.replace("ROOT/'results/control'","ROOT/'results/control_v2'").replace("ROOT/'results/artifact_manifest.json'","ROOT/'results/artifact_manifest_v2.json'")
text=text.replace("gate=[];metrics=[];ticks=0","gate=[];metrics=[];ticks=0;baseline_completed={};probe_completed={};reused_baselines=0")
needle="        actual,log=replay(c,p,LoggedBase);expected=gz(c['trace_file']);result=compare(actual,expected,c['board_reference'])"
replacement="""        oldfolder=ROOT/'results/control'/c['id']
        if (oldfolder/'baseline_trace.json.gz').exists():
            actual=gz(oldfolder/'baseline_trace.json.gz');log=load(oldfolder/'baseline_focus.json');reused_baselines+=1
        else:actual,log=scheduled_replay(c,p,LoggedBase,baseline_completed)
        expected=gz(c['trace_file']);result=compare(actual,expected,c['board_reference'])"""
assert text.count(needle)==1;text=text.replace(needle,replacement)
needle="        actual,log=replay(c,p,LoggedProbe);folder=out/c['id'];"
assert text.count(needle)==1;text=text.replace(needle,"        actual,log=scheduled_replay(c,p,LoggedProbe,probe_completed);folder=out/c['id'];")
text=text.replace("'all_raw_and_existing_traces_unchanged':True,","'all_raw_and_existing_traces_unchanged':True,'hardware_Toros_pair_update_order_reproduced':True,'reused_successful_failed_run_baselines':reused_baselines,")
text=text.replace("    p=load(ROOT/'protocol/control_v2.json');e=load(ROOT/'protocol/execution_v2.json')","    p=load(ROOT/'protocol/control_v2.json');e=load(ROOT/'protocol/execution_v2.json')\n    for r in load(ROOT/'protocol/failed_baselines_preserved.json'):assert sha(ROOT/r['file'])==r['sha256']")
text=text.replace("    save(out/'summary.json',summary)","    for r in load(ROOT/'protocol/failed_baselines_preserved.json'):assert sha(ROOT/r['file'])==r['sha256']\n    save(out/'summary.json',summary)")
ast.parse(text);script=ROOT/'tools/run_control_v2.py';assert not script.exists();script.write_text(text,encoding='utf-8',newline='\n')
p=load(ROOT/'protocol/control_v1.json');p.update({'status':'FROZEN_ORIGINAL_HARDWARE_MULTI_SAMPLER_ORDER_BEFORE_ANY_CONTROL_VARIANT',
    'created_host_UTC':datetime.now(timezone.utc).isoformat(),'previous_failed_job':'130637','previous_probe_job':'130638',
    'hardware_Toros_execution_order':'create_two_pipelines_then_update_each_source_frame_stride6_then_stride1;shared_STrack_ID_allocator_reproduced',
    'CPU_nonhardware_cache_order_unchanged':True,'no_ID_relabeling_or_event_tolerance_relaxation':True,
    'failed_probe_print_TypeError_after_six_diagnostic_records_saved':True,'all_old_outputs_preserved':True,
    'successful_prior_baselines_reused_no_tracker_rerun':True,'all_baselines_must_pass_before_probe':True})
save(ROOT/'protocol/control_v2.json',p)
job=(ROOT/'tools/control.slurm').read_text(encoding='utf-8').replace('control-%j','control-v2-%j').replace('tools/run_control.py','tools/run_control_v2.py')
f=ROOT/'tools/control_v2.slurm';assert not f.exists();f.write_text(job,encoding='utf-8',newline='\n')
files=[script,ROOT/'tools/confirmation_iou.py',f,*sorted(x for x in (ROOT/'input').glob('*') if x.is_file())]
save(ROOT/'protocol/execution_v2.json',{'protocol_sha256':sha(ROOT/'protocol/control_v2.json'),'files_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in files}})
a=ROOT/'control_inputs_v2.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for f in [script,ROOT/'tools/control_v2.slurm',ROOT/'protocol/control_v2.json',ROOT/'protocol/execution_v2.json']:tar.add(f,arcname=f.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'/control_inputs_v2.tar.gz'],check=True)
cmd='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130637,130638 -X --format=JobID,State,ExitCode,Elapsed -P
cd REMOTE/PHASE
../env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json,subprocess
for job in ['130637','130638']:
 assert subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('FAILED|1:0')
old=Path('results/control');files=sorted(p for p in old.rglob('*') if p.is_file())
assert len(list(old.glob('*/baseline_trace.json.gz')))==91
manifest=Path('protocol/failed_baselines_preserved.json');assert not manifest.exists()
manifest.write_text(json.dumps([{'file':p.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2)+'\\n')
a=Path('control_inputs_v2.tar.gz');assert hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=Path(m.name);assert not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
print('RETAIN91_BASELINES;REPRODUCE_HARDWARE_SAMPLER_ORDER;IDS_EVENTS_STILL_EXACT_REQUIRED')
PY
sbatch --parsable tools/control_v2.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/submit_v2.sh';assert not f.exists();f.write_text(cmd,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/submission_v2.txt')],check=True)
