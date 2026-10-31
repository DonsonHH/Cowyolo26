"""Rerun every observed schedule through the frozen tracker, on Slurm CPU."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,gzip,os,socket,sys,traceback
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
plan=load(ROOT/'tracker_input/protocol.json')
for row in plan['files']:assert sha(ROOT/row['file'])==row['sha256']
sys.path.insert(0,str(ROOT/'tracker_input/source'))
from frame_pipeline import FramePipeline

def decode(raw):
 boxes=raw[raw[:,4]>=.2].copy();gain=192/1440
 # The source crop1050W x1440H is rotated: decode sees1440W x1050H.
 px=round((192-1440*gain)/2-.1);py=round((192-1050*gain)/2-.1)
 boxes[:,[0,2]]=(boxes[:,[0,2]]-px)/gain;boxes[:,[1,3]]=(boxes[:,[1,3]]-py)/gain
 boxes[:,[0,2]]=np.clip(boxes[:,[0,2]],0,1440);boxes[:,[1,3]]=np.clip(boxes[:,[1,3]],0,1050)
 return [{'xyxy':[float(v[1])+870,1440-float(v[2]),float(v[3])+870,1440-float(v[0])],'confidence':float(v[4]),'class':0}for v in boxes]

out=ROOT/'results/tracker_replay';out.mkdir(parents=True,exist_ok=False);reports=[];total=boxes=0
state={'status':'RUNNING','Slurm_job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),'new_model_forwards':0,'whole_goal_complete':False}
try:
 history=gz(ROOT/'tracker_input/history.json.gz')
 for case in plan['cases']:
  trace=gz(ROOT/case['trace']);pipeline=FramePipeline(plan['video'],plan['tracker_config'],plan['counter_kwargs'])
  actual={k:[]for k in['observations','post_tracker','confirmed_only_events','handoff_events']}
  with np.load(ROOT/case['raw'])as a:frames=a['frame0'].copy();raw=a['raw'].copy()
  rows=[(r['frame0'],r['predictions'])for r in history]+[(int(frame),decode(v))for frame,v in zip(frames,raw)]
  for frame,predictions in rows:
   result=pipeline.update(frame,predictions);actual['observations'].append(result['observation'])
   for key in['post_tracker','confirmed_only_events','handoff_events']:actual[key].extend(result[key])
  actual=json.loads(json.dumps(actual));maxbox=maxaxis=0.
  for key in['confirmed_only_events','handoff_events']:assert actual[key]==trace[key],(case['run'],key)
  assert len(actual['observations'])==len(trace['observations'])and len(actual['post_tracker'])==len(trace['post_tracker'])
  for a,b in zip(actual['post_tracker'],trace['post_tracker']):
   assert all(a[k]==b[k]for k in['frame0','time_s','track_id','confidence'])
   delta=max(abs(x-y)for x,y in zip(a['xyxy'],b['xyxy']));maxbox=max(maxbox,delta);assert delta<=.002
  for a,b in zip(actual['observations'],trace['observations']):
   assert all(a[k]==b[k]for k in['frame0','time_s','confirmed_IDs'])
   for field in['confirmed_positions','tentative_positions']:
    assert a[field].keys()==b[field].keys()
    for key in a[field]:delta=abs(a[field][key]-b[field][key]);maxaxis=max(maxaxis,delta);assert delta<=2e-6
   assert len(a['accepted_history'])==len(b['accepted_history'])
   for x,y in zip(a['accepted_history'],b['accepted_history']):
    assert all(x[k]==y[k]for k in['track_id','observation_time_s','confirmation_time_s'])
    delta=abs(x['axis_position']-y['axis_position']);maxaxis=max(maxaxis,delta);assert delta<=2e-6
  total+=len(rows);boxes+=len(actual['post_tracker']);reports.append({'run':case['run'],'observation_ticks':len(rows),'post_tracker_rows':len(actual['post_tracker']),'IDs_and_events_exact':True,'maximum_box_difference':maxbox,'maximum_axis_difference':maxaxis})
  with gzip.GzipFile(filename=str(out/(case['run']+'_actual_trace.json.gz')),mode='wb',mtime=0)as f:f.write(json.dumps(actual,separators=(',',':')).encode())
 assert len(reports)==8 and'torch'not in sys.modules
 state.update({'status':'ALL8_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES','created_UTC':datetime.now(timezone.utc).isoformat(),'observation_ticks':total,'post_tracker_rows':boxes,'reports':reports,'counter_paths':16,'maximum_box_tolerance_pixels':.002,'maximum_axis_tolerance':2e-6,'Torch_imported':False})
except BaseException as e:state.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc()});raise
finally:(out/'summary.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state),flush=True)
