"""Run cached detections through the installed tracker. No detector forward or training."""
from pathlib import Path
from collections import defaultdict
import copy,csv,hashlib,json,os,socket,sys,time
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML,IterableSimpleNamespace
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'tracker_clock_20261028'
sys.path.insert(0,str(PROJECT/'phase2/tools'))
from zone_counter import ZoneCounter

FIELDS=['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,value):Path(p).write_text(json.dumps(value,indent=2))
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def normal(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
def writecsv(p,rows):
    with Path(p).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)

def run(p,source,buffer,names,name,exact):
    folder=Path(source['remote_folder']);dest=ROOT/'results'/name;dest.mkdir(exist_ok=False)
    boxes=defaultdict(list)
    for row in read(folder/'pretracker_boxes.csv'):
        boxes[int(row['frame'])].append([*[float(row[k]) for k in ['x1','y1','x2','y2']],float(row['confidence']),next(k for k,v in names.items() if v=='cow')])
    original=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');args=copy.deepcopy(original);args['track_buffer']=buffer
    tracker=BYTETracker(IterableSimpleNamespace(**args));counter=ZoneCounter(stable_samples=source['stable_samples'])
    image=np.zeros((1440,2560,3),dtype=np.uint8);rows=[];history=[];events=[];state_log=[];started=time.perf_counter()
    stride=source['stride']
    for frame in range(0,10874,stride):
        array=np.asarray(boxes.get(frame,[]),dtype=np.float32).reshape(-1,6)
        result=Results(orig_img=image,path='cached_native_frame',names=names,boxes=torch.from_numpy(array))
        tracked=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
        if len(tracked):
            result=result[tracked[:,-1].astype(int)];result.update(boxes=torch.as_tensor(tracked[:,:-1]))
        positions={};b=result.boxes
        ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b)
        for box,confidence,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
            x1,y1,x2,y2=box
            if tid is None or not .34<(x1+x2)/5120<.75:continue
            row=dict(zip(FIELDS,[frame,frame/25,tid,confidence,x1,y1,x2,y2,(y1+y2)/2880]))
            positions[tid]=row['axis_position'];(rows if frame>=8912 else history).append(row)
        for event in counter.update(frame/25,positions):
            event['source_frame']=frame
            if frame>=8912:events.append(event)
        if frame>=8912:
            state_log.append({'frame':frame,'tracker_update':tracker.frame_id,'live_IDs':sorted(positions),
              'lost_IDs':[r.track_id for r in tracker.lost_stracks],'removed_IDs':[r.track_id for r in tracker.removed_stracks]})
    writecsv(dest/'source_tracks.csv',rows);writecsv(dest/'source_warmup_tracks.csv',history)
    save(dest/'source_events.json',events);save(dest/'scoped_tracker_states.json',state_log)
    if exact:
        assert normal(rows)==normal(read(folder/'source_tracks.csv')),(name,'ROI track mismatch')
        assert normal(history)==normal(read(folder/'source_warmup_tracks.csv')),(name,'history mismatch')
        assert events==load(folder/'source_events.json'),(name,'event mismatch')
    summary={'name':name,'cached_source':source['name'],'seed':source['seed'],'stride':stride,
       'inference_Hz':25/stride,'track_buffer':buffer,'nominal_lost_budget_s':buffer/(25/stride),
       'stable_samples':source['stable_samples'],'predicted_down':sum(e['direction']=='A->B' for e in events),
       'predicted_up':sum(e['direction']=='B->A' for e in events),'ROI_track_IDs':len({r['track_id'] for r in rows}),
       'ROI_track_rows':len(rows),'history_rows':len(history),'exact_prior_replay_required':exact,
       'exact_tracks_history_events_match':True if exact else None,'elapsed_s':time.perf_counter()-started,
       'effective_tracker_config':args,'only_tracker_config_difference':{k:[original[k],args[k]] for k in args if original[k]!=args[k]},
       'detector_forwards':0,'training_updates':0,'independent_accuracy':None,'board_execution':False}
    save(dest/'summary.json',summary);print(json.dumps(summary),flush=True);return summary

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    torch.set_num_threads(2)
    path=ROOT/'protocol/clock_v1.json';p=load(path);assert ultralytics.__version__=='8.4.63'
    source_files={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for row in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/source_files[row['file']])==row['sha256']
    names={}
    for w in p['weights']:
        assert sha(w['checkpoint'])==w['sha256'];model=YOLO(w['checkpoint']);names[w['seed']]=model.names
        assert 'cow' in model.names.values();del model
    for source in p['sources']:
        for f in source['files']:
            path=Path(source['remote_folder'])/f['name'];assert path.stat().st_size==f['bytes'] and sha(path)==f['sha256']
    results=[]
    for source in p['sources']:
        results.append(run(p,source,p['baseline_buffer'],names[source['seed']],'exact_'+source['name'],True))
    assert len(results)==p['required_exact_replays_before_controls']
    save(ROOT/'results/exact_replay_gate.json',{'status':'FIVE_CACHED_RAW_TO_TRACK_HISTORY_EVENT_REPLAYS_EXACT','conditions':results,
                                             'protocol_sha256':sha(ROOT/'protocol/clock_v1.json')})
    for c in p['controls']:
        source=next(r for r in p['sources'] if r['name']==c['source'])
        results.append(run(p,source,c['track_buffer'],names[source['seed']],c['name'],False))
    save(ROOT/'results/summary.json',{'status':'FIVE_EXACT_REPLAYS_AND_TWO_FIXED_BUFFER_CONTROLS_COMPLETED',
       'job_id':os.environ['SLURM_JOB_ID'],'host':socket.gethostname(),'protocol_sha256':sha(ROOT/'protocol/clock_v1.json'),
       'conditions':results,'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy':None,
       'board_execution':False,'whole_goal_complete':False})
if __name__=='__main__':main()
