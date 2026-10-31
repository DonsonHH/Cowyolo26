"""Read-only state probe; require unchanged full replay before interpreting cases."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,sys
import numpy as np,torch
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML,IterableSimpleNamespace
import ultralytics
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/tracker_clock_20261028');PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'phase2/tools'))
from zone_counter import ZoneCounter
FIELDS=['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position']
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def norm(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
    p=load(ROOT/'protocol/clock_v1.json');q=load(ROOT/'protocol/case_probe_v1.json')
    assert q['clock_protocol_sha256']==sha(ROOT/'protocol/clock_v1.json')
    destination=ROOT/'results/case_probe';destination.mkdir(exist_ok=False);records=[]
    for case in q['cases']:
        source=next(s for s in p['sources'] if s['name']==case['source']);folder=Path(source['remote_folder'])
        assert sha(folder/'pretracker_boxes.csv')==next(f['sha256'] for f in source['files'] if f['name']=='pretracker_boxes.csv')
        weight=next(w for w in p['weights'] if w['seed']==source['seed']);model=YOLO(weight['checkpoint']);names=model.names;del model
        cow=next(k for k,v in names.items() if v=='cow');raw=defaultdict(list)
        for r in read(folder/'pretracker_boxes.csv'):raw[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),cow])
        args=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');assert args['track_buffer']==30
        tracker=BYTETracker(IterableSimpleNamespace(**args));counter=ZoneCounter(stable_samples=3)
        image=np.zeros((1440,2560,3),np.uint8);tracks=[];history=[];events=[];observations=[];tid=case['target_ID']
        for frame in range(0,10874,5):
            array=np.asarray(raw[frame],np.float32).reshape(-1,6);result=Results(orig_img=image,path='cache',names=names,boxes=torch.from_numpy(array))
            tracked=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
            if len(tracked):result=result[tracked[:,-1].astype(int)];result.update(boxes=torch.as_tensor(tracked[:,:-1]))
            b=result.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b);positions={}
            for box,conf,identity in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
                x1,y1,x2,y2=box
                if identity is None or not .34<(x1+x2)/5120<.75:continue
                row=dict(zip(FIELDS,[frame,frame/25,identity,conf,x1,y1,x2,y2,(y1+y2)/2880]))
                positions[identity]=row['axis_position'];(tracks if frame>=8912 else history).append(row)
            for e in counter.update(frame/25,positions):
                e['source_frame']=frame
                if frame>=8912:events.append(e)
            if q['inspect_range'][0]<=frame<=q['inspect_range'][1]:
                internal=[]
                for label,pool in [('tracked_pool',tracker.tracked_stracks),('lost_pool',tracker.lost_stracks),('removed_pool',tracker.removed_stracks)]:
                    for t in pool:
                        if t.track_id==tid:internal.append({'pool':label,'is_activated':bool(t.is_activated),'state':int(t.state),
                           'start_source_frame':(t.start_frame-1)*5,'last_tracker_source_frame':(t.frame_id-1)*5,'score':float(t.score)})
                state=counter.states.get(tid)
                observations.append({'source_frame':frame,'target_ID':tid,'target_output_y':positions.get(tid),
                   'target_tracker_state':internal,'counter_state':vars(state).copy() if state else None,
                   'all_raw_boxes':raw[frame],'ROI_output_IDs':sorted(positions)})
        assert norm(tracks)==norm(read(folder/'source_tracks.csv'))
        assert norm(history)==norm(read(folder/'source_warmup_tracks.csv')) and events==load(folder/'source_events.json')
        assert not any(e['track_id']==tid for e in events)
        output=destination/f'seed{source["seed"]}_ID{tid}.json';output.write_text(json.dumps(observations,indent=2))
        records.append({'seed':source['seed'],'target_ID':tid,'full_original_tracks_history_events_exact':True,
                        'target_emitted_events':0,'inspected_frames':len(observations),'trace_file':output.name,'sha256':sha(output)})
    record={'status':'THREE_INSTRUMENTED_FULL_REPLAYS_EXACT_STATE_PROBES_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
        'probe_protocol_sha256':sha(ROOT/'protocol/case_probe_v1.json'),'cases':records,
        'posthoc_development_diagnosis':True,'independent_event_truth':False,'new_detector_forwards':0,'training_updates':0}
    (destination/'summary.json').write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
if __name__=='__main__':main()
