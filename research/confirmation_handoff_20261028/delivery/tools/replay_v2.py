from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,os,socket,subprocess,sys
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker,STrack
from ultralytics.utils import YAML,IterableSimpleNamespace
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/confirmation_handoff_20261028')
OUT=ROOT/'results/replay_v2'
sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
FIELDS=['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position']
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))
def norm(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
def csvsave(p,rows):
    with Path(p).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
def run(p,source):
    folder=Path(source['remote_folder']);seed=source['seed'];dest=OUT/f'seed{seed}';dest.mkdir(exist_ok=False)
    weight=next(w for w in p['weights'] if w['seed']==seed);assert sha(weight['checkpoint'])==weight['sha256']
    model=YOLO(weight['checkpoint']);names=model.names;del model;cow=next(k for k,v in names.items() if v=='cow')
    raw=defaultdict(list)
    for row in read(folder/'pretracker_boxes.csv'):raw[int(row['frame'])].append([*[float(row[k]) for k in ['x1','y1','x2','y2']],float(row['confidence']),cow])
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');assert cfg['track_buffer']==30
    tracker=BYTETracker(IterableSimpleNamespace(**cfg));original=ZoneCounter(**p['counter'])
    disabled=ConfirmationHandoffCounter(**p['counter'],retain_prior=False);candidate=ConfirmationHandoffCounter(**p['counter'])
    events0=[];eventsoff=[];events1=[];rows=[];history=[];traces=[];accepts=[];image=np.zeros((1440,2560,3),np.uint8)
    for frame in range(0,10874,5):
        result=Results(orig_img=image,path='cached_native',names=names,boxes=torch.from_numpy(np.asarray(raw[frame],np.float32).reshape(-1,6)))
        tracked=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
        if len(tracked):result=result[tracked[:,-1].astype(int)];result.update(boxes=torch.as_tensor(tracked[:,:-1]))
        b=result.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b)
        positions={};active={tid for tid in ids if tid is not None};tentative={}
        for box,confidence,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
            x1,y1,x2,y2=box
            if tid is None or not .34<(x1+x2)/5120<.75:continue
            row=dict(zip(FIELDS,[frame,frame/25,tid,confidence,x1,y1,x2,y2,(y1+y2)/2880]))
            positions[tid]=row['axis_position'];(rows if frame>=8912 else history).append(row)
        for t in tracker.tracked_stracks:
            if t.is_activated:continue
            x1,y1,x2,y2=np.asarray(t.xyxy,dtype=np.float32).astype(float)
            if .34<(x1+x2)/5120<.75:tentative[t.track_id]=(y1+y2)/2880
        outputs=[original.update(frame/25,positions),disabled.update(frame/25,positions,tentative,active),candidate.update(frame/25,positions,tentative,active)]
        for out,target in zip(outputs,[events0,eventsoff,events1]):
            for e in out:
                e['source_frame']=frame
                if frame>=8912:target.append(e)
        accepted=[{**r,'observation_source_frame':round(r['observation_time_s']*25),'confirmation_source_frame':frame} for r in candidate.last_acceptances]
        accepts+=accepted
        traces.append({'source_frame':frame,'confirmed_positions':positions,'confirmed_ids':sorted(active),
                       'tentative_positions':tentative,'accepted_history':accepted})
    assert norm(rows)==norm(read(folder/'source_tracks.csv')) and norm(history)==norm(read(folder/'source_warmup_tracks.csv'))
    assert events0==load(folder/'source_events.json') and eventsoff==events0
    key=lambda e:(e['source_frame'],e['track_id'],e['direction']);a=Counter(map(key,events0));b=Counter(map(key,events1))
    added=[e for e in events1 if (b-a)[key(e)]];removed=[e for e in events0 if (a-b)[key(e)]]
    csvsave(dest/'source_tracks.csv',rows);csvsave(dest/'source_warmup_tracks.csv',history)
    for name,value in [('baseline_events.json',events0),('disabled_events.json',eventsoff),('handoff_events.json',events1),('observations.json',traces),('history_acceptances.json',accepts)]:save(dest/name,value)
    record={'seed':seed,'baseline_down':sum(e['direction']=='A->B' for e in events0),'handoff_down':sum(e['direction']=='A->B' for e in events1),
      'baseline_up':sum(e['direction']=='B->A' for e in events0),'handoff_up':sum(e['direction']=='B->A' for e in events1),
      'added_events':added,'removed_events':removed,'all_prior_tracks_history_events_exact':True,'disabled_wrapper_events_exact':True,
      'history_acceptances_total':len(accepts),'history_acceptances_in_scope':sum(r['confirmation_source_frame']>=8912 for r in accepts),
      'maximum_simultaneous_pending_IDs':candidate.maximum_pending_tracks,'samples_per_pending_ID_limit':1,
      'ROI_track_rows':len(rows),'history_track_rows':len(history),'effective_tracker_config':cfg,
      'independent_source_accuracy':None,'new_detector_forwards':0,'training_updates':0,'board_execution':False}
    save(dest/'summary.json',record);print(json.dumps(record),flush=True);return record
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
    OUT.mkdir(exist_ok=False)
    probe=STrack(np.asarray([100.,100.,40.,50.,0.],np.float32),.9,0)
    assert np.array_equal(probe.xyxy,np.array([80.,75.,120.,125.]))
    p=load(ROOT/'protocol/handoff_v1.json');assert sha(ROOT/'input/zone_counter.py')==p['frozen_base_counter_sha256']
    assert sha(ROOT/'tools/confirmation_counter.py')==p['handoff_module_sha256'] and ultralytics.__version__=='8.4.63'
    mapping={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for f in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/mapping[f['file']])==f['sha256']
    for s in p['sources']:
        for f in s['files']:assert sha(Path(s['remote_folder'])/f['name'])==f['sha256']
    test=subprocess.run([sys.executable,str(ROOT/'tools/test_handoff.py')],capture_output=True)
    (OUT/'behavior_server_green.txt').write_bytes(test.stdout+test.stderr);assert test.returncode==0
    results=[run(p,s) for s in p['sources']]
    save(OUT/'summary.json',{'status':'THREE_FROZEN_CACHED_TRACKERS_PAIRED_COUNTER_HANDOFF_COMPLETE',
      'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/handoff_v1.json'),'module_sha256':sha(ROOT/'tools/confirmation_counter.py'),
      'conditions':results,'behavior_tests':14,'new_detector_forwards':0,'training_updates':0,
      'independent_source_accuracy':None,'board_execution':False,'whole_goal_complete':False})
if __name__=='__main__':main()
