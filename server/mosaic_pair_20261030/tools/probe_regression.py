from pathlib import Path
from datetime import datetime,timezone
import os,socket,sys,json,gzip,hashlib
import numpy as np,cv2,torch,ultralytics
from ultralytics import YOLO
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
assert torch.cuda.is_available();torch.set_num_threads(4);cv2.setNumThreads(1)
sys.path.insert(0,str(PROJECT/'pynq_frontend_port_20261029'))
from frame_pipeline import FramePipeline
def load(p):return json.loads(Path(p).read_text())
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
p=load(ROOT/'protocol/evaluation_v1.json');rows=[]
for video in p['videos']:
    for seed in [26,27,28]:
        folder=PROJECT/'factorial_lane_crop_20261029/results/roi'/video['name']/('S192_rot90_seed'+str(seed))
        raw=gz(folder/'raw_predictions.json.gz');byframe={r['frame0']:r['predictions'] for r in raw}
        for stride in video['counter_replay_strides']:
            pipe=FramePipeline(video,p['tracker_config'],p['counter_kwargs'])
            trace={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
            for frame in range(0,video['decode_end_exclusive'],stride):
                value=pipe.update(frame,byframe[frame]);trace['observations'].append(value['observation'])
                for key in ['post_tracker','confirmed_only_events','handoff_events']:trace[key].extend(value[key])
            actual=json.loads(json.dumps(trace));expected=gz(folder/('stride'+str(stride)+'_counter_trace.json.gz'))
            differences=[];maxbox=maxaxis=maxother=0.;structural=0
            def compare(a,b,path=''):
                if isinstance(a,dict) and isinstance(b,dict):
                    if set(a)!=set(b):differences.append({'path':path,'kind':'dict_keys','actual':sorted(a),'expected':sorted(b)})
                    for k in sorted(set(a)&set(b)):compare(a[k],b[k],path+'.'+k)
                elif isinstance(a,list) and isinstance(b,list):
                    if len(a)!=len(b):differences.append({'path':path,'kind':'length','actual':len(a),'expected':len(b)})
                    for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'.'+str(i))
                elif a!=b:
                    numeric=isinstance(a,(float,int)) and isinstance(b,(float,int)) and not isinstance(a,bool) and not isinstance(b,bool)
                    differences.append({'path':path,'kind':'numeric' if numeric else 'value','actual':a,'expected':b,'absolute_error':abs(a-b) if numeric else None})
            compare(actual,expected)
            counts={};maxima={}
            for d in differences:
                kind='structure'
                if d['kind']=='numeric':
                    if '.xyxy.' in d['path']:kind='box_pixels'
                    elif any(k in d['path'] for k in ['confirmed_positions','tentative_positions','axis_position']):kind='normalized_axis'
                    else:kind='other_numeric'
                counts[kind]=counts.get(kind,0)+1
                if d.get('absolute_error') is not None:maxima[kind]=max(maxima.get(kind,0.),d['absolute_error'])
            rows.append({'scene':video['name'],'seed':seed,'stride':stride,'observation_ticks':len(actual['observations']),
                'entire_trace_exact':not differences,'confirmed_events_exact':actual['confirmed_only_events']==expected['confirmed_only_events'],
                'handoff_events_exact':actual['handoff_events']==expected['handoff_events'],'difference_counts':counts,'maximum_errors':maxima,
                'first12_differences':differences[:12]})
result={'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'hostname':socket.gethostname(),
    'new_network_forwards':0,'counter_or_tracker_parameters_changed':False,'rows':rows,'whole_goal_complete':False}
dest=ROOT/'results/regression_diagnostic.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
