from pathlib import Path
import os,json,hashlib,tarfile,traceback
from pynq import PL
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
try:
 s=load(ROOT/'results/record.json');t=load(ROOT/'results/terminal.json');p=load(ROOT/'run_protocol.json')
 assert s['status']==t['status']=='ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE'
 assert t['record_sha256']==sha(ROOT/'results/record.json') and t['close_error'] is None and not (Path('/proc')/str(t['PID'])).exists()
 assert s['actual_O8_forwards']==sum(r['processed_frames'] for r in s['cases']) and len(s['cases'])==6
 assert s['qualification_forwards']==8 and s['warmup_forwards']==12 and s['PL_after_sha256']==p['O8_bit_sha256']==sha(Path(PL.bitfile_name))
 children=[]
 for run in p['runs']:
  if run['policy']=='foreground_only':continue
  folder=ROOT/'results'/run['run']/'background';bt=load(folder/'terminal.json');b=load(folder/'record.json')
  assert bt['status']==b['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and bt['record_sha256']==sha(folder/'record.json')
  assert not (Path('/proc')/str(bt['PID'])).exists() and len(b['jobs'])==b['model_forwards']
  children.append({'PID':bt['PID'],'proc_exists':False,'jobs':len(b['jobs']),'run':run['run']})
 write(ROOT/'final_state.json',{'status':'SIX_RUN_PARENT_AND_FOUR_IDENTITY_WORKERS_TERMINAL_ABSENT_O8_RETAINED','PID':t['PID'],'proc_exists':False,
  'children':children,'PL_bitfile':PL.bitfile_name,'PL_bit_sha256':sha(Path(PL.bitfile_name)),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'memory':Path('/proc/meminfo').read_text()})
 files=[f for f in sorted((ROOT/'results').rglob('*')) if f.is_file()]
 files.extend(ROOT/name for name in ['run_protocol.json','board_causal_repeats.py','background_selected_worker.py','causal_selector.py','collect_results.py','launch.json','run.log','final_state.json'])
 manifest=ROOT/'result_manifest.json';write(manifest,[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files])
 archive=ROOT/'causal_photo_delivery_v1.tar.gz';assert not archive.exists()
 with tarfile.open(archive,'w:gz') as tar:
  for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
 os.sync();transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
 write(ROOT/'transfer.json',transfer);write(ROOT/'collection_terminal.json',{'status':'RESULT_ARCHIVE_COMPLETE','PID':os.getpid(),'transfer':transfer})
 print(json.dumps(transfer),flush=True)
except BaseException as e:
 write(ROOT/'collection_terminal.json',{'status':'FAILED','PID':os.getpid(),'error':repr(e),'traceback':traceback.format_exc()});raise
