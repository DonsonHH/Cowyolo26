"""Actual ARM NumPy/LAP tracker regression, independent of model inference."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,gzip,hashlib,time,traceback
ROOT=Path(__file__).resolve().parent
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
sys.path.insert(0,str(ROOT/'source/lap-0.5.13'))
import numpy as np,lap
from frame_pipeline import FramePipeline
def load(p):return json.loads(p.read_text())
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 q=p.with_suffix(p.suffix+'.partial');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def normalize(x):return json.loads(json.dumps(x))
def main():
 p=load(ROOT/'board_regression_v1.json');out=ROOT/'regression_results';out.mkdir(exist_ok=False)
 for r in p['files']:assert sha(ROOT/r['file'])==r['sha256']
 assert np.__version__=='1.21.5' and lap.__version__=='0.5.13'
 state={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'protocol_sha256':sha(ROOT/'board_regression_v1.json'),'reports':[],'observation_ticks':0,'post_tracker_rows':0,
        'maximum_box_pixel_difference':0.,'maximum_normalized_axis_difference':0.,'real_network_forwards':0,'PL_actions':0,'whole_goal_complete':False}
 started=time.perf_counter_ns()
 try:
  for source in p['caches']:
   rawpath=ROOT/source['raw_file'];tracepath=ROOT/source['trace_file']
   assert sha(rawpath)==source['raw_sha256'] and sha(tracepath)==source['trace_sha256']
   raw=gz(rawpath);expected=gz(tracepath);byframe={r['frame0']:r['predictions'] for r in raw}
   pipeline=FramePipeline(source['spec'],p['tracker_config'],p['counter_kwargs'])
   actual={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[],'effective_tracker_config':p['tracker_config']}
   for frame in range(0,source['spec']['decode_end_exclusive'],source['stride']):
    result=pipeline.update(frame,byframe[frame]);actual['observations'].append(result['observation'])
    for name in ['post_tracker','confirmed_only_events','handoff_events']:actual[name].extend(result[name])
   actual=normalize(actual)
   assert actual['confirmed_only_events']==expected['confirmed_only_events'] and actual['handoff_events']==expected['handoff_events']
   assert actual['effective_tracker_config']==expected['effective_tracker_config']
   assert len(actual['post_tracker'])==len(expected['post_tracker']) and len(actual['observations'])==len(expected['observations'])
   maxbox=maxaxis=0.
   for a,b in zip(actual['post_tracker'],expected['post_tracker']):
    assert all(a[k]==b[k] for k in ['frame0','time_s','track_id','confidence'])
    error=max(abs(x-y) for x,y in zip(a['xyxy'],b['xyxy']));maxbox=max(maxbox,error)
    assert error<=p['board_coordinate_tolerance_pixels']
   for a,b in zip(actual['observations'],expected['observations']):
    assert all(a[k]==b[k] for k in ['frame0','time_s','confirmed_IDs'])
    for name in ['confirmed_positions','tentative_positions']:
     assert a[name].keys()==b[name].keys()
     for key,value in a[name].items():
      error=abs(value-b[name][key]);maxaxis=max(maxaxis,error);assert error<=p['board_normalized_axis_tolerance']
    assert len(a['accepted_history'])==len(b['accepted_history'])
    for x,y in zip(a['accepted_history'],b['accepted_history']):
     assert all(x[k]==y[k] for k in ['track_id','observation_time_s','confirmation_time_s'])
     error=abs(x['axis_position']-y['axis_position']);maxaxis=max(maxaxis,error);assert error<=p['board_normalized_axis_tolerance']
   state['observation_ticks']+=len(actual['observations']);state['post_tracker_rows']+=len(actual['post_tracker'])
   state['maximum_box_pixel_difference']=max(state['maximum_box_pixel_difference'],maxbox)
   state['maximum_normalized_axis_difference']=max(state['maximum_normalized_axis_difference'],maxaxis)
   state['reports'].append({k:source[k] for k in ['mode','scene','condition','stride']}|{'observation_ticks':len(actual['observations']),'max_box_difference':maxbox,'max_axis_difference':maxaxis,'IDs_and_events_exact':True})
   write(out/'progress.json',{'status':state['status'],'PID':os.getpid(),'completed_traces':len(state['reports']),'observation_ticks':state['observation_ticks']})
   print(json.dumps(state['reports'][-1]),flush=True)
  assert len(state['reports'])==90 and state['observation_ticks']==82020 and state['post_tracker_rows']==40893
  assert 'torch' not in sys.modules
  state.update({'status':'ALL90_REAL_ARM_TRACES180_COUNTER_PATHS82020_TICKS_PASS_FROZEN_TOLERANCES',
                'torch_imported':False,'counter_paths':180,'numpy':np.__version__,'lap':lap.__version__})
 except BaseException as e:
  state.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc(),'failed_source':source if 'source' in locals() else None})
  if 'actual' in locals():write(out/'failed_actual.json',actual)
 finally:
  state['wall_s']=(time.perf_counter_ns()-started)/1e9;write(out/'summary.json',state)
  write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),'completed_traces':len(state['reports']),'summary_sha256':sha(out/'summary.json')})
  print(json.dumps({k:v for k,v in state.items() if k!='reports'}),flush=True)
 if state['status']=='FAILED':raise SystemExit(1)
if __name__=='__main__':main()
