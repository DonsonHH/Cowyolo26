"""Preserve original output while observing the installed association path."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,sys
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker,STrack,TrackState
from ultralytics.trackers.utils import matching
from ultralytics.utils import YAML,IterableSimpleNamespace
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/paired_event_intake_20261028');PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'phase2/tools'))
from zone_counter import ZoneCounter
FIELDS=['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))
def normal(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
def description(t):
    return {'track_ID':int(t.track_id),'state':int(t.state),'activated':bool(t.is_activated),
            'xyxy':np.asarray(t.xyxy).tolist(),'score':float(t.score),'input_detection_index':int(t.idx)}
def det_description(d):return {'input_detection_index':int(d.idx),'confidence':float(d.score),'xyxy':np.asarray(d.xyxy).tolist()}
class TraceTracker(BYTETracker):
    def __init__(self,args,target):super().__init__(args);self.target=target;self.record=None;self.stage=None
    def _first_association(self,pool,detections,activated,refind):
        if self.record is not None:
            index=next((i for i,t in enumerate(pool) if t.track_id==self.target),None)
            self.record['first_target_pool_index']=index
            self.record['first_high_detections']=[det_description(d) for d in detections]
            self.record['first_target_predicted']=description(pool[index]) if index is not None else None
            self.record['first_target_costs']=self.get_dists(pool,detections)[index].tolist() if index is not None and detections else []
        self.stage='first';out=super()._first_association(pool,detections,activated,refind)
        if self.record is not None:self.record['first_unmatched_IDs']=[int(pool[i].track_id) for i in out[0]]
        return out
    def _second_association(self,pool,u_track,detections,activated,refind,lost):
        if self.record is not None:
            target=next((t for t in pool if t.track_id==self.target),None)
            eligible=[pool[i] for i in u_track if pool[i].state==TrackState.Tracked]
            self.record['second_eligible_IDs']=[int(t.track_id) for t in eligible]
            self.record['second_target_eligible']=any(t.track_id==self.target for t in eligible)
            self.record['second_low_detections']=[det_description(d) for d in detections]
            # Diagnostic geometry is recorded even if a lost target is ineligible.
            if target is not None and detections:
                raw=matching.iou_distance([target],detections);fused=matching.fuse_score(raw,detections) if self.args.fuse_score else raw
                self.record['second_diagnostic_target_IoUs']=(1-raw[0]).tolist()
                self.record['second_diagnostic_target_costs']=fused[0].tolist()
            else:self.record.update(second_diagnostic_target_IoUs=[],second_diagnostic_target_costs=[])
        self.stage='second';return super()._second_association(pool,u_track,detections,activated,refind,lost)
    def _apply_match(self,track,det,activated,refind):
        if self.record is not None and track.track_id==self.target:
            self.record['target_applied_matches'].append({'stage':self.stage,'target_before_match':description(track),'detection':det_description(det)})
        return super()._apply_match(track,det,activated,refind)
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
    protocol=ROOT/'protocol/exit_probe_v1.json';p=load(protocol);assert ultralytics.__version__=='8.4.63'
    mapping={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for item in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/mapping[item['file']])==item['sha256']
    assert sha(Path(ultralytics.__path__[0])/'trackers/utils/matching.py')==p['matching_source_sha256']
    dest=ROOT/'results/exit_probe';dest.mkdir(exist_ok=False);source=Path(p['source']['remote_folder'])
    for row in p['source']['files']:assert sha(source/row['name'])==row['sha256']
    assert sha(p['weights']['checkpoint'])==p['weights']['sha256'];model=YOLO(p['weights']['checkpoint']);names=model.names;del model
    cow=next(k for k,v in names.items() if v=='cow');raw=defaultdict(list)
    for r in read(source/'pretracker_boxes.csv'):raw[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),cow])
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');tracker=TraceTracker(IterableSimpleNamespace(**cfg),p['target_ID'])
    counter=ZoneCounter();tracks=[];history=[];events=[];records=[];image=np.zeros((1440,2560,3),np.uint8)
    for frame in range(0,10874,5):
        active=frame in p['probe_frames'];tracker.record={'source_frame':frame,'raw_boxes':raw[frame],'target_applied_matches':[]} if active else None
        result=Results(orig_img=image,path='cache',names=names,boxes=torch.from_numpy(np.asarray(raw[frame],np.float32).reshape(-1,6)))
        tracked=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
        if len(tracked):result=result[tracked[:,-1].astype(int)];result.update(boxes=torch.as_tensor(tracked[:,:-1]))
        b=result.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b);positions={};all_IDs=[tid for tid in ids if tid is not None]
        for box,confidence,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
            x1,y1,x2,y2=box
            if tid is None or not .34<(x1+x2)/5120<.75:continue
            row=dict(zip(FIELDS,[frame,frame/25,tid,confidence,x1,y1,x2,y2,(y1+y2)/2880]))
            (tracks if frame>=8912 else history).append(row);positions[tid]=row['axis_position']
        current=counter.update(frame/25,positions)
        for e in current:
            e['source_frame']=frame
            if frame>=8912:events.append(e)
        if active:
            target=next((t for pool in [tracker.tracked_stracks,tracker.lost_stracks] for t in pool if t.track_id==p['target_ID']),None)
            tracker.record.update(target_after=description(target) if target is not None else None,
                target_confirmed_output=p['target_ID'] in all_IDs,target_output_in_ROI=p['target_ID'] in positions,
                target_axis=positions.get(p['target_ID']),counter_state=vars(counter.states[p['target_ID']]).copy() if p['target_ID'] in counter.states else None,
                first_threshold=float(cfg['match_thresh']),second_threshold=.5,high_threshold=float(cfg['track_high_thresh']),
                low_threshold=float(cfg['track_low_thresh']),fuse_score=cfg['fuse_score'])
            records.append(tracker.record)
    assert normal(tracks)==normal(read(source/'source_tracks.csv')) and normal(history)==normal(read(source/'source_warmup_tracks.csv'))
    assert events==load(source/'source_events.json') and not any(e['track_id']==p['target_ID'] for e in events)
    save(dest/'association_trace.json',records)
    # Probe installed cost fusion/assignment itself, including ideal IoU=1.
    score_values=[.100001,.15,.2,.223299,.249999];ious=[0.,.25,.5,.9,1.]
    detections=[STrack(np.array([50.,50.,40.,40.,j],np.float32),score,0) for j,score in enumerate(score_values)]
    cost=np.repeat((1-np.asarray(ious,np.float32))[:,None],len(score_values),axis=1)
    fused=matching.fuse_score(cost,detections);matches,ua,ub=matching.linear_assignment(fused,thresh=.5)
    assert len(matches)==0 and np.min(fused)>.75
    grid={'detection_scores':score_values,'IoUs':ious,'installed_fused_costs':fused.tolist(),'secondstage_threshold':.5,
          'matches':np.asarray(matches).tolist(),'all25_pairs_rejected':True,'grid_is_synthetic_not_cattle_accuracy':True}
    save(dest/'low_score_cost_grid.json',grid)
    summary={'status':'ORIGINAL_FULL_REPLAY_EXACT_ELEVEN_ASSOCIATION_FRAMES_AND_COST_GRID_CAPTURED',
       'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(protocol),'seed':28,'target_ID':p['target_ID'],
       'full_tracks_history_events_exact':True,'unchanged_original_down_events':len(events),'observed_frames':len(records),
       'target_output_frames':[r['source_frame'] for r in records if r['target_output_in_ROI']],
       'synthetic_cost_grid_pairs':25,'new_detector_forwards':0,'training_updates':0,
       'independent_source_accuracy':None,'board_execution':False,'whole_goal_complete':False}
    save(dest/'summary.json',summary);print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
