"""Exact full cached replay and a six-update, real-tracker recovery signal."""
from pathlib import Path
from collections import defaultdict
import argparse,csv,hashlib,json,os,pickle,socket,sys,time
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.trackers.basetrack import BaseTrack
from ultralytics.utils import YAML,IterableSimpleNamespace
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/long_video_track_gap_20261029')
sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
def read(p):
    with Path(p).open(newline='') as f:return list(csv.DictReader(f))
def normal(rows):
    return [{k:(int(v) if v not in ['',None] else None) if k in ['frame0','track_id'] else float(v) for k,v in row.items()} for row in rows]

def step(tracker,base,counter,frame,array,names,image):
    result=Results(orig_img=image,path='native_cached',names=names,boxes=torch.from_numpy(array))
    tracked=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
    if len(tracked):result=result[tracked[:,-1].astype(int)];result.update(boxes=torch.as_tensor(tracked[:,:-1]))
    b=result.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b)
    active={tid for tid in ids if tid is not None};positions={};tentative={};post=[];tracks=[]
    for box,confidence,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
        x1,y1,x2,y2=box
        row=dict(zip(['frame0','time_s','track_id','confidence','x1','y1','x2','y2'],[frame,frame/25,tid,confidence,*box]));post.append(row)
        if tid is not None and .34<(x1+x2)/5120<.75:
            cy=(y1+y2)/2880;positions[tid]=cy;tracks.append({**row,'axis_position':cy})
    for t in tracker.tracked_stracks:
        if t.is_activated:continue
        x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float)
        if .34<(x1+x2)/5120<.75:tentative[int(t.track_id)]=(y1+y2)/2880
    generated=[base.update(frame/25,positions),counter.update(frame/25,positions,tentative,active)]
    for events in generated:
        for e in events:e['frame0']=frame
    observation={'frame0':frame,'time_s':frame/25,'confirmed_positions':positions,'confirmed_IDs':sorted(active),
                 'tentative_positions':tentative,'accepted_history':counter.last_acceptances}
    return post,tracks,observation,generated

def guards(p):
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    assert ultralytics.__version__=='8.4.63';torch.set_num_threads(2)
    mapping={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for r in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/mapping[r['file']])==r['sha256']
    assert sha(Path(ultralytics.__path__[0])/'trackers/utils/matching.py')==p['matching_source_sha256']
    for name,digest in p['input_modules'].items():assert sha(ROOT/'input'/name)==digest

def recovery_signal():
    p=load(ROOT/'protocol/reproduce_v1.json');guards(p)
    record=load(ROOT/'results/reproduce/snapshot_record.json');path=ROOT/'results/reproduce/before_02650.pkl'
    assert sha(path)==record['sha256'];data=pickle.loads(path.read_bytes())
    tracker,base,counter=data['tracker'],data['base'],data['counter'];BaseTrack._count=data['base_track_count']
    image=np.zeros((1440,2560,3),np.uint8)
    outputs=[];events=[];start=time.perf_counter()
    for frame,array in data['frames']:
        _,_,obs,generated=step(tracker,base,counter,frame,array,data['names'],image)
        assert json.loads(json.dumps(obs))==data['expected_observations'][str(frame)]
        outputs.append({'frame0':frame,'confirmed_positions':obs['confirmed_positions']});events.extend(generated[1])
    target=p['target_ID'];restored=any(target in r['confirmed_positions'] and r['confirmed_positions'][target]>.6 for r in outputs)
    counted=any(e['track_id']==target and e['direction']=='A->B' for e in events)
    verdict={'status':'PASS' if restored and counted else 'FAIL_EXPECTED_BASELINE_GAP',
             'signal_is_independent_human_GT':False,'original_ID19_recovered_in_B':restored,'original_ID19_A_to_B_emitted':counted,
             'real_tracker_updates':len(outputs),'outputs':outputs,'events':events,'loop_elapsed_s':time.perf_counter()-start,
             'new_detector_forwards':0,'new_training_updates':0}
    print(json.dumps(verdict),flush=True)
    return 0 if restored and counted else 1

def full_replay():
    p=load(ROOT/'protocol/reproduce_v1.json');guards(p);source=Path(p['source_folder'])
    for r in p['source_files']:assert (source/r['name']).stat().st_size==r['bytes'] and sha(source/r['name'])==r['sha256']
    assert sha(p['weights']['checkpoint'])==p['weights']['sha256']
    model=YOLO(p['weights']['checkpoint']);names=model.names;del model;cow=next(k for k,v in names.items() if v=='cow')
    raw=defaultdict(list)
    for row in read(source/'raw_detector_boxes.csv'):
        raw[int(row['frame'])].append([*[float(row[k]) for k in ['x1','y1','x2','y2']],float(row['confidence']),cow])
    arrays={f:np.asarray(raw[f],np.float32).reshape(-1,6) for f in range(0,10125,5)}
    args=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml')
    tracker=BYTETracker(IterableSimpleNamespace(**args));base=ZoneCounter(**p['counter']);counter=ConfirmationHandoffCounter(**p['counter'])
    out=ROOT/'results/reproduce';out.mkdir(parents=True,exist_ok=False)
    expected_obs=load(source/'observations.json')
    post=[];tracks=[];obs=[];base_events=[];events=[];image=np.zeros((1440,2560,3),np.uint8);start=time.perf_counter()
    for frame,array in arrays.items():
        if frame==2650:
            snapshot={'tracker':tracker,'base':base,'counter':counter,'names':names,'base_track_count':BaseTrack._count,
                      'expected_observations':{str(r['frame0']):r for r in expected_obs if r['frame0'] in p['short_replay_frames']},
                      'frames':[(f,arrays[f]) for f in p['short_replay_frames']]}
            target=out/'before_02650.pkl';target.write_bytes(pickle.dumps(snapshot,protocol=5))
            save(out/'snapshot_record.json',{'path':target.name,'sha256':sha(target),'bytes':target.stat().st_size,'source_frame0':2650,
                 'trusted_project_generated_pickle_only':True,'contains_raw_neighbours_and_complete_tracker_state':True})
        a,b,c,d=step(tracker,base,counter,frame,array,names,image)
        post.extend(a);tracks.extend(b);obs.append(c);base_events.extend(d[0]);events.extend(d[1])
    assert post==normal(read(source/'post_tracker_boxes.csv')),'full post-tracker outputs differ'
    assert tracks==normal(read(source/'tracks.csv')),'full native ROI outputs differ'
    assert json.loads(json.dumps(obs))==expected_obs,'observations or tentative history differ'
    assert base_events==load(source/'confirmed_only_events_all_history.json') and events==load(source/'handoff_events_all_history.json')
    assert len(events)==11 and not any(e['track_id'] in [19,23] for e in events)
    save(out/'summary.json',{'status':'SEED26_FULL_RAW_TRACK_OBSERVATION_AND_TWO_EVENT_PATHS_REPLAY_EXACT',
         'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/reproduce_v1.json'),
         'cached_tracker_updates':len(obs),'full_post_rows':len(post),'native_ROI_rows':len(tracks),
         'all_tentative_and_admitted_history_exact':True,'confirmed_only_down':len(base_events),'handoff_down':len(events),
         'missing_original_ID19_event_reproduced':True,'full_replay_elapsed_s':time.perf_counter()-start,
         'new_detector_forwards':0,'new_training_updates':0,'formal_scores_computed':False,'whole_goal_complete':False})
    print(json.dumps(load(out/'summary.json')),flush=True)
    return 0

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--signal',action='store_true');args=parser.parse_args()
    return recovery_signal() if args.signal else full_replay()
if __name__=='__main__':raise SystemExit(main())
