from datetime import datetime,timezone
import hashlib,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from pynq import PL,Clocks
p=Path(__file__).resolve().parent;protocol=json.loads((p/'protocol.json').read_bytes())
runtime=Path(protocol['source_runtime'])
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for data in iter(lambda:f.read(1048576),b''):h.update(data)
 return h.hexdigest()
def save(state):
 q=p/'batch_status.writing';q.write_text(json.dumps(state,indent=2)+'\n');q.replace(p/'batch_status.json')
assert os.geteuid()==0 and os.uname().nodename=='pynq'
assert not (p/'batch_status.json').exists()
state={'status':'PREFLIGHT','PID':os.getpid(),'started_UTC':datetime.now(timezone.utc).isoformat(),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'completed':[]}
save(state)
try:
 assert sha(runtime.parent/'source.tar.gz')==protocol['source_archive_sha256']
 for name,digest in protocol['source_file_sha256'].items():assert sha(runtime/name)==digest,name
 for name,digest in protocol['hardware_model_assets_sha256'].items():assert sha(name)==digest,name
 assert PL.bitfile_name.endswith('/optimization_8_resident.bit')
 assert abs(Clocks.fclk0_mhz-100)<.01
 env=dict(os.environ,XILINX_XRT='/usr',PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
   PYTHONPATH=str(runtime)+':/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029/source/lap-0.5.13')
 for item in protocol['cases']:
  tag=item['tag'];clip=protocol['clips'][item['clip']];case=p/tag;case.mkdir()
  assert sha(clip['source'])==clip['source_sha256']
  assert shutil.disk_usage('/dev/shm').free>Path(clip['source']).stat().st_size+32*1048576
  cfg=dict(clip['config']);cfg['session_id']='ram_io_control_'+tag
  cp=case/'config.json';cp.write_text(json.dumps(cfg,indent=2)+'\n')
  ram=Path(tempfile.mkdtemp(prefix='cow-io-control-',dir='/dev/shm')).resolve()
  assert ram.parent==Path('/dev/shm') and ram.name.startswith('cow-io-control-')
  stage=time.monotonic();shutil.copyfile(clip['source'],ram/'input.avi')
  assert sha(ram/'input.avi')==clip['source_sha256']
  staging_s=time.monotonic()-stage
  freeze={'case':item,'config_sha256':sha(cp),'source_sha256':clip['source_sha256'],
   'runtime_archive_sha256':protocol['source_archive_sha256'],'protocol_sha256':sha(p/'protocol.json'),
   'boot_id':state['boot_id'],'ram_input':str(ram/'input.avi'),'media_staging_s':staging_s}
  (case/'freeze.json').write_text(json.dumps(freeze,indent=2)+'\n')
  try:
   with (ram/'run.log').open('xb') as log:
    child=subprocess.Popen([sys.executable,'-m','counting.budget_runner','--source',str(ram/'input.avi'),
     '--config',str(cp),'--policy',item['policy'],'--output',str(ram/'output')],
     cwd=runtime,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
    state.update(status='RUNNING',current=tag,child_PID=child.pid);save(state)
    try:code=child.wait(timeout=300)
    except subprocess.TimeoutExpired:
     child.terminate()
     try:child.wait(timeout=15)
     except subprocess.TimeoutExpired:child.kill();child.wait()
     raise RuntimeError('Timed RAM case exceeded300s; retain partial workload')
   copy_start=time.monotonic()
   if (ram/'output').exists():shutil.copytree(ram/'output',case/'output')
   shutil.copyfile(ram/'run.log',case/'run.log')
   binding={}
   for source in ram.rglob('*'):
    if source.is_file() and source.name!='input.avi':
     relative=source.relative_to(ram).as_posix()
     assert sha(source)==sha(case/relative),relative
     binding[relative]={'bytes':source.stat().st_size,'sha256':sha(source)}
   storage={'input_sha256':clip['source_sha256'],'input_bytes':(ram/'input.avi').stat().st_size,
    'media_staging_s':staging_s,'copyback_s':time.monotonic()-copy_start,'copied_output_sha256':binding,
    'storage_copy_inside_stream':False,'new_model_calls_for_copy':0}
   (case/'storage_receipt.json').write_text(json.dumps(storage,indent=2)+'\n')
  finally:
   # Only this freshly-created task-owned RAM directory is removed.
   assert ram.parent==Path('/dev/shm') and ram.name.startswith('cow-io-control-')
   shutil.rmtree(ram)
  sp=case/'output/summary.json';summary=json.loads(sp.read_bytes()) if sp.exists() else None
  terminal={'exit_code':code,'summary_sha256':sha(sp) if sp.exists() else None,
            'runtime_status':summary.get('status') if summary else 'MISSING_SUMMARY'}
  (case/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n')
  assert code==0 and summary and summary['status']=='COMPLETED_UNSCORED',terminal
  assert summary['budget']['executed_real_calls']==clip['planned_real_calls']
  assert summary['video_sha256']==clip['source_sha256'] and not summary['software_fixture_only']
  state['completed'].append(tag);save(state)
 for name,digest in protocol['source_file_sha256'].items():assert sha(runtime/name)==digest,name
 for name,digest in protocol['hardware_model_assets_sha256'].items():assert sha(name)==digest,name
 state.update(status='COMPLETED',ended_UTC=datetime.now(timezone.utc).isoformat());save(state)
except BaseException as error:
 state.update(status='FAILED',error=repr(error),ended_UTC=datetime.now(timezone.utc).isoformat());save(state)
 raise
