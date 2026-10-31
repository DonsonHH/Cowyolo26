from pathlib import Path
import csv,hashlib,json,os,socket,sys
from collections import defaultdict
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker,TrackState
from ultralytics.utils import YAML,IterableSimpleNamespace
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/external_method_regression_20261028')
sys.path.insert(0,str(ROOT/'input'))
from secondstage_tracker import SecondStageIoUTracker,verify_method_scope as cost_scope
from lost_tracker import LostLowScoreTracker,verify_method_scope as lost_scope
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
from event_metrics import evaluate_events
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))
def writecsv(p,rows,fields):
    with Path(p).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def normalized(rows):
    return [{k:None if v in [None,''] else int(v) if k in ['frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
class AuditMixin:
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.in_second=False;self.low_matches=[]
    def _second_association(self,*a,**kw):
        self.in_second=True
        try:return super()._second_association(*a,**kw)
        finally:self.in_second=False
    def _apply_match(self,track,det,activated,refind):
        if self.in_second:self.low_matches.append({'frame':self.frame_id-1,'track_id':int(track.track_id),
              'state_before':int(track.state),'confidence':float(det.score),'gap_frames':self.frame_id-int(track.frame_id)})
        return super()._apply_match(track,det,activated,refind)
class Original(AuditMixin,BYTETracker):pass
class IoU(AuditMixin,SecondStageIoUTracker):pass
class Lost(AuditMixin,LostLowScoreTracker):pass
def event_ledger(reference,prediction,metrics):
    rows=[]
    for pair in metrics['pairs']:
        i,j=pair['reference_index'],pair['prediction_index'];r=reference[i];p=prediction[j]
        rows.append({'kind':'correct_direction_match' if pair['direction_correct'] else 'wrong_direction_match',
             'reference_ID':r['track_id'],'reference_frame':r['frame'],'prediction_ID':p['track_id'],'prediction_frame':p['frame'],
             'time_error_s':pair['time_error_s'],'reference_direction':r['direction'],'prediction_direction':p['direction']})
    for i in metrics['unmatched_reference_indices']:
        r=reference[i];rows.append({'kind':'unmatched_reference','reference_ID':r['track_id'],'reference_frame':r['frame'],'reference_direction':r['direction']})
    for j in metrics['unmatched_prediction_indices']:
        r=prediction[j];rows.append({'kind':'unmatched_prediction','prediction_ID':r['track_id'],'prediction_frame':r['frame'],'prediction_direction':r['direction']})
    return rows
def run(p,model,names,variant):
    name=model['name']+'_'+variant;folder=ROOT/'results'/name;folder.mkdir(exist_ok=False)
    cache=Path(next(r['path'] for r in model['cache_files'] if r['path'].endswith('/raw_detector_boxes.csv'))).parent
    raw=defaultdict(list);cow=next(k for k,v in names.items() if v=='cow')
    for r in read(cache/'raw_detector_boxes.csv'):raw[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),cow])
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');tracker={'installed':Original,'secondstage_iou':IoU,'allow_lost_iou':Lost}[variant](IterableSimpleNamespace(**cfg))
    ordinary=ZoneCounter(**p['counter']);handoff=ConfirmationHandoffCounter(**p['counter'])
    tracks=[];post=[];events0=[];events1=[];trace=[];image=np.zeros((1080,1920,3),np.uint8)
    for frame in range(479):
        r=Results(orig_img=image,path='cached_toros',names=names,boxes=torch.from_numpy(np.asarray(raw[frame],np.float32).reshape(-1,6)))
        output=tracker.update(r.boxes.cpu().numpy(),r.orig_img,feats=None)
        if len(output):r=r[output[:,-1].astype(int)];r.update(boxes=torch.as_tensor(output[:,:-1]))
        b=r.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b);active={i for i in ids if i is not None};positions={};tentative={}
        for box,score,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
            x1,y1,x2,y2=box;cx=(x1+x2)/3840;cy=(y1+y2)/2160
            post.append({'frame':frame,'time_s':frame/30,'track_id':tid,'confidence':score,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
            if tid is not None and .1<cy<.95:
                positions[tid]=cx;tracks.append({'frame':frame,'time_s':frame/30,'track_id':tid,'axis_position':cx,'cy_norm':cy})
        for t in tracker.tracked_stracks:
            if not t.is_activated:
                x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float)
                if .1<(y1+y2)/2160<.95:tentative[int(t.track_id)]=(x1+x2)/3840
        for out,target in [(ordinary.update(frame/30,positions),events0),(handoff.update(frame/30,positions,tentative,active),events1)]:
            for e in out:e['frame']=frame;target.append(e)
        trace.append({'frame':frame,'confirmed_positions':positions,'confirmed_IDs':sorted(active),'tentative_positions':tentative,
          'accepted_history':[{**r,'observation_frame':round(r['observation_time_s']*30),'confirmation_frame':frame} for r in handoff.last_acceptances]})
    if variant=='installed':
        assert normalized(post)==normalized(read(cache/'post_tracker_boxes.csv')),'posttrackerbaseline drift'
        assert normalized(tracks)==normalized(read(cache/'tracks.csv')),'ROIbaseline drift'
        assert events0==model['prior_events'],'originaleventbaseline drift'
    writecsv(folder/'post_tracker_boxes.csv',post,['frame','time_s','track_id','confidence','x1','y1','x2','y2'])
    writecsv(folder/'tracks.csv',tracks,['frame','time_s','track_id','axis_position','cy_norm'])
    save(folder/'confirmed_only_events.json',events0);save(folder/'handoff_events.json',events1);save(folder/'observations.json',trace);save(folder/'low_matches.json',tracker.low_matches)
    scores=[]
    for counter_name,events in [('confirmed_only',events0),('handoff',events1)]:
        m=evaluate_events(p['reference_events'],events,2.)
        if variant=='installed' and counter_name=='confirmed_only':assert m['TP']==model['expected_prior_TP'] and m['FP']==0
        scores.append({'condition_id':name+'_'+counter_name,'model':model['name'],'tracker_variant':variant,'counter_variant':counter_name,
           'main_method':variant=='installed' or counter_name=='handoff','metrics':m,'event_ledger':event_ledger(p['reference_events'],events,m),
           'events_path':(folder/(counter_name+'_events.json')).relative_to(ROOT).as_posix(),
           'reference_authority':'Already-used publisher trajectory-derived six-event diagnostic reference; no new test claim'})
    record={'name':name,'model':model['name'],'variant':variant,'checkpoint_sha256':model['checkpoint']['sha256'],'frames':479,
        'raw_rows':sum(map(len,raw.values())),'posttracker_rows':len(post),'ROI_rows':len(tracks),'ROI_IDs':len({r['track_id'] for r in tracks}),
        'confirmed_only_events':len(events0),'handoff_events':len(events1),'baseline_exact':variant=='installed',
        'low_stage_matches':len(tracker.low_matches),'low_Lost_recoveries':sum(r['state_before']==int(TrackState.Lost) for r in tracker.low_matches),
        'scores':scores,'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False}
    save(folder/'summary.json',record);print(json.dumps(record),flush=True);return record
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
    protocol=ROOT/'protocol/regression_v1.json';p=load(protocol);assert ultralytics.__version__=='8.4.63'
    mapping={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for row in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/mapping[row['file']])==row['sha256']
    assert sha(Path(ultralytics.__path__[0])/'trackers/utils/matching.py')==p['matching_source_sha256']
    for name,checksum in p['input_modules'].items():assert sha(ROOT/'input'/name)==checksum
    refmeta=p['reference_author_summary'];assert sha(refmeta['path'])==refmeta['sha256']
    assert load(refmeta['path'])['events']==p['reference_events'] and sha(ROOT/'input/publisher_gt_original.txt')==p['publisher_GT_sha256']
    scopes={'cost_scope':cost_scope(),'lost_scope':lost_scope()};save(ROOT/'results/method_scope_verification.json',scopes)
    conditions=[]
    for model in p['models']:
        for row in [model['checkpoint'],*model['cache_files']]:assert sha(row['path'])==row['sha256']
        detector=YOLO(model['checkpoint']['path']);names=detector.names;del detector
        for variant in p['variants']:conditions.append(run(p,model,names,variant))
    scores=[r for c in conditions for r in c['scores']];assert len(scores)==12 and sum(r['main_method'] for r in scores)==8
    summary={'status':'TWO_FIXED_DETECTOR_CACHES_SIX_TRACKER_RUNS_TWELVE_REFERENCED_COUNTER_PATHS_SCORED',
       'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(protocol),'reference_events':p['reference_events'],
       'conditions':conditions,'scores':scores,'main_method_conditions':8,'diagnostic_additional_conditions':4,
       'new_detector_forwards':0,'training_updates':0,'new_independent_test':False,'MultiCam_source_truth_received':False,
       'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(ROOT/'results/summary.json',summary)
    fields=['condition_id','model','tracker_variant','counter_variant','main_method','reference_events','predicted_events','TP','FP','FN','wrong_direction_matches','precision','recall','f1']
    with (ROOT/'results/scored_conditions.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] if k in r else r['metrics'][k] for k in fields} for r in scores)
if __name__=='__main__':main()
