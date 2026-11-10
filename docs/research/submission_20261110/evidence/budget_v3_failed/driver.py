from datetime import datetime,timezone
import hashlib,json,os,subprocess,sys,tarfile,time
from pathlib import Path
from pynq import PL,Clocks
p=Path(__file__).resolve().parent
protocol=json.loads((p/'protocol.json').read_bytes());runtime=Path(protocol['source_runtime'])
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return h.hexdigest()
def save(value):
 t=p/'batch_status.writing';t.write_text(json.dumps(value,indent=2)+'\n');t.replace(p/'batch_status.json')
assert os.geteuid()==0 and os.uname().nodename=='pynq'
assert not (p/'batch_status.json').exists(),'Inspect the existing batch; do not resubmit.'
state={'status':'PREFLIGHT','PID':os.getpid(),'started_UTC':datetime.now(timezone.utc).isoformat(),
       'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'completed':[]}
save(state)
try:
 assert sha(runtime.parent/'source.tar.gz')==protocol['source_archive_sha256']
 for name,digest in protocol['source_file_sha256'].items():assert sha(runtime/name)==digest,name
 for name,digest in protocol['hardware_model_assets_sha256'].items():assert sha(name)==digest,name
 for clip in protocol['clips'].values():assert sha(clip['source'])==clip['source_sha256']
 assert json.loads((runtime/'software_status.json').read_bytes())['exit_code']==0
 assert '177 tests' in (runtime/'software_tests.log').read_text()
 assert PL.bitfile_name.endswith('/optimization_8_resident.bit'),PL.bitfile_name
 assert abs(Clocks.fclk0_mhz-100)<0.01,Clocks.fclk0_mhz
 state.update(status='RUNNING',PL_bitfile=PL.bitfile_name,FCLK0_MHz=Clocks.fclk0_mhz)
 save(state)
 env=dict(os.environ,XILINX_XRT='/usr',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',
  OPENBLAS_NUM_THREADS='1',PYTHONPATH=str(runtime)+':/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029/source/lap-0.5.13')
 for item in protocol['cases']:
  tag=item['tag'];clip=protocol['clips'][item['clip']];case=p/tag;case.mkdir()
  cfg=dict(clip['config']);cfg['session_id']='equal_budget_v3_'+tag
  cp=case/'config.json';cp.write_text(json.dumps(cfg,indent=2)+'\n')
  case_freeze={'case':item,'config_sha256':sha(cp),'source_sha256':clip['source_sha256'],
    'runtime_archive_sha256':protocol['source_archive_sha256'],'protocol_sha256':sha(p/'protocol.json'),
    'boot_id':state['boot_id'],'before_process_UTC':datetime.now(timezone.utc).isoformat()}
  (case/'freeze.json').write_text(json.dumps(case_freeze,indent=2)+'\n')
  with (case/'run.log').open('xb') as log:
   child=subprocess.Popen([sys.executable,'-m','counting.budget_runner','--source',clip['source'],
     '--config',str(cp),'--policy',item['policy'],'--output',str(case/'output')],
     cwd=runtime,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
   state.update(current=tag,child_PID=child.pid);save(state)
   try:code=child.wait(timeout=protocol['source_timeout_s'])
   except subprocess.TimeoutExpired:
    child.terminate()
    try:child.wait(timeout=15)
    except subprocess.TimeoutExpired:child.kill();child.wait()
    raise RuntimeError('case300s observation bound; inspect retained partial workload')
  sp=case/'output/summary.json';summary=json.loads(sp.read_bytes()) if sp.exists() else None
  receipt={'exit_code':code,'summary_sha256':sha(sp) if sp.exists() else None,
   'runtime_status':summary.get('status') if summary else 'MISSING_SUMMARY',
   'after_process_UTC':datetime.now(timezone.utc).isoformat()}
  (case/'terminal.json').write_text(json.dumps(receipt,indent=2)+'\n')
  assert code==0 and summary and summary['status']=='COMPLETED_UNSCORED',receipt
  assert not summary['software_fixture_only']
  assert summary['budget']['executed_real_calls']==clip['planned_real_calls']
  assert summary['model_forwards']==clip['planned_real_calls']+1
  assert summary['video_sha256']==clip['source_sha256']
  assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==state['boot_id']
  state['completed'].append(tag);save(state)
 for name,digest in protocol['source_file_sha256'].items():assert sha(runtime/name)==digest,name
 for name,digest in protocol['hardware_model_assets_sha256'].items():assert sha(name)==digest,name
 state.update(status='COMPLETED',ended_UTC=datetime.now(timezone.utc).isoformat());save(state)
except BaseException as error:
 state.update(status='FAILED',error=repr(error),ended_UTC=datetime.now(timezone.utc).isoformat());save(state)
 raise
