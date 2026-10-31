from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,subprocess,sys
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import TrackState
from ultralytics.trackers.utils import matching
from ultralytics.utils import YAML,IterableSimpleNamespace
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/lost_recovery_20261028')
sys.path.insert(0,str(ROOT/'input'))
from secondstage_tracker import SecondStageIoUTracker
from lost_tracker import LostLowScoreTracker,verify_method_scope
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
from event_metrics import evaluate_events
FIELDS=['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text())
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))
def norm(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
def writecsv(p,rows,fields=FIELDS):
    with Path(p).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

class AuditMixin:
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw);self.allow_lost=isinstance(self,LostLowScoreTracker);self.decisions=[];self.current=None;self.second_calls=0
    def _second_association(self,pool,unmatched,low,activated,refind,lost):
        self.second_calls+=1
        states=(TrackState.Tracked,TrackState.Lost) if self.allow_lost else (TrackState.Tracked,)
        eligible=[pool[i] for i in unmatched if pool[i].state in states]
        if eligible and low:
            costs=matching.iou_distance(eligible,low)
            decision={'source_frame':(self.frame_id-1)*5,'eligible_IDs':[int(t.track_id) for t in eligible],
              'eligible_states':[int(t.state) for t in eligible],
              'eligible_last_observed_frames':[(int(t.frame_id)-1)*5 for t in eligible],
              'eligible_xyxy':[np.asarray(t.xyxy).tolist() for t in eligible],
              'excluded_IDs':[int(pool[i].track_id) for i in unmatched if pool[i].state not in states],
              'low_detections':[{'stage_local_index':int(d.idx),'xyxy':np.asarray(d.xyxy).tolist(),'confidence':float(d.score)} for d in low],
              'costs':costs.tolist(),'threshold':.5,'allows_lost':self.allow_lost,'applied_pairs':[]}
            self.decisions.append(decision);self.current=decision
        else:self.current=None
        try:return super()._second_association(pool,unmatched,low,activated,refind,lost)
        finally:self.current=None
    def _apply_match(self,track,det,activated,refind):
        if self.current is not None:
            d=self.current;i=d['eligible_IDs'].index(int(track.track_id));j=int(det.idx)
            d['applied_pairs'].append({'row_index':i,'low_stage_index':j,'track_ID':int(track.track_id),
              'state_before':int(track.state),'last_observed_source_frame':(int(track.frame_id)-1)*5,
              'observation_gap_source_frames':(self.frame_id-int(track.frame_id))*5,
              'cost':d['costs'][i][j],'confidence':float(det.score)})
        return super()._apply_match(track,det,activated,refind)
class ActiveAudit(AuditMixin,SecondStageIoUTracker):pass
class LostAudit(AuditMixin,LostLowScoreTracker):pass

def run(p,source,names,variant):
    seed=source['seed'];name=f'{variant}_seed{seed}';folder=ROOT/'results'/name;folder.mkdir(exist_ok=False)
    raw=defaultdict(list);cow=next(k for k,v in names.items() if v=='cow')
    for r in read(Path(source['remote_folder'])/'pretracker_boxes.csv'):raw[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),cow])
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');assert cfg['fuse_score'] is True and cfg['track_buffer']==30
    tracker=(ActiveAudit if variant=='active_only_iou' else LostAudit)(IterableSimpleNamespace(**cfg))
    ordinary=ZoneCounter(**p['counter']);counter=ConfirmationHandoffCounter(**p['counter'])
    tracks=[];history=[];allrows=[];events0=[];events1=[];traces=[];image=np.zeros((1440,2560,3),np.uint8)
    for frame in range(0,10874,5):
        r=Results(orig_img=image,path='cached_native',names=names,boxes=torch.from_numpy(np.asarray(raw[frame],np.float32).reshape(-1,6)))
        out=tracker.update(r.boxes.cpu().numpy(),r.orig_img,feats=None)
        if len(out):r=r[out[:,-1].astype(int)];r.update(boxes=torch.as_tensor(out[:,:-1]))
        b=r.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b);active={i for i in ids if i is not None};positions={};tentative={}
        for box,score,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
            x1,y1,x2,y2=box;allrows.append({'source_frame':frame,'track_id':tid,'confidence':score,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
            if tid is None or not .34<(x1+x2)/5120<.75:continue
            row=dict(zip(FIELDS,[frame,frame/25,tid,score,x1,y1,x2,y2,(y1+y2)/2880]));positions[tid]=row['axis_position'];(tracks if frame>=8912 else history).append(row)
        for t in tracker.tracked_stracks:
            if not t.is_activated:
                x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float)
                if .34<(x1+x2)/5120<.75:tentative[int(t.track_id)]=(y1+y2)/2880
        for out,target in [(ordinary.update(frame/25,positions),events0),(counter.update(frame/25,positions,tentative,active),events1)]:
            for e in out:
                e['source_frame']=frame
                if frame>=8912:target.append(e)
        traces.append({'source_frame':frame,'confirmed_positions':positions,'confirmed_IDs':sorted(active),'tentative_positions':tentative,
                       'accepted_history':[{**a,'observation_source_frame':round(a['observation_time_s']*25),'confirmation_source_frame':frame} for a in counter.last_acceptances]})
    assert tracker.second_calls==2175
    if variant=='active_only_iou':
        prior=Path(next(s for s in p['prior_baselines'] if s['seed']==seed)['remote_folder'])
        assert norm(tracks)==norm(read(prior/'source_tracks.csv')) and norm(history)==norm(read(prior/'source_warmup_tracks.csv'))
        assert events0==load(prior/'confirmed_only_events.json') and events1==load(prior/'handoff_events.json')
        fields=['source_frame','track_id','confidence','x1','y1','x2','y2']
        def allnorm(rows):return [{k:None if v in [None,''] else int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
        assert allnorm(allrows)==allnorm(read(prior/'all_posttracker_boxes.csv'))
    writecsv(folder/'source_tracks.csv',tracks);writecsv(folder/'source_warmup_tracks.csv',history)
    writecsv(folder/'all_posttracker_boxes.csv',allrows,['source_frame','track_id','confidence','x1','y1','x2','y2'])
    for f,value in [('confirmed_only_events.json',events0),('handoff_events.json',events1),('observations.json',traces),('secondstage_decisions.json',tracker.decisions)]:save(folder/f,value)
    pairs=[{**a,'source_frame':d['source_frame']} for d in tracker.decisions for a in d['applied_pairs']]
    lostpairs=[a for a in pairs if a['state_before']==int(TrackState.Lost)]
    writecsv(folder/'lost_low_recoveries.csv',lostpairs,['row_index','low_stage_index','track_ID','state_before','last_observed_source_frame','observation_gap_source_frames','cost','confidence','source_frame'])
    record={'name':name,'variant':variant,'seed':seed,'predicted_down':sum(e['direction']=='A->B' for e in events1),
      'predicted_up':sum(e['direction']=='B->A' for e in events1),'confirmed_only_down':sum(e['direction']=='A->B' for e in events0),
      'confirmed_only_up':sum(e['direction']=='B->A' for e in events0),'ROI_track_rows':len(tracks),'history_track_rows':len(history),
      'ROI_track_IDs':len({r['track_id'] for r in tracks}),'ROI_tracked_frames':len({r['source_frame'] for r in tracks}),
      'nonempty_secondstage_decisions':len(tracker.decisions),'low_matches_all_history':len(pairs),
      'low_matches_in_scope':sum(a['source_frame']>=8912 for a in pairs),'lost_recoveries_all_history':len(lostpairs),
      'lost_recoveries_in_scope':sum(a['source_frame']>=8912 for a in lostpairs),
      'maximum_lost_recovery_gap_frames':max((a['observation_gap_source_frames'] for a in lostpairs),default=None),
      'baseline_full_regression_exact':variant=='active_only_iou','effective_default_config':cfg,
      'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy':None,'FPGA_execution_verified':False}
    save(folder/'summary.json',record);print(json.dumps(record),flush=True);return record
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
    p=load(ROOT/'protocol/lost_v1.json');assert ultralytics.__version__=='8.4.63'
    assert sha(ROOT/'tools/lost_tracker.py')==p['candidate_module_sha256']
    for name,checksum in p['input_modules'].items():assert sha(ROOT/'input'/name)==checksum
    mapping={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for row in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/mapping[row['file']])==row['sha256']
    assert sha(Path(ultralytics.__path__[0])/'trackers/utils/matching.py')==p['matching_source_sha256']
    for s in p['sources']:
        for f in s['files']:assert sha(Path(s['remote_folder'])/f['name'])==f['sha256']
    for s in p['prior_baselines']:
        for f in s['files']:assert sha(Path(s['remote_folder'])/f['name'])==f['sha256']
    test=subprocess.run([sys.executable,str(ROOT/'tools/test_real_gate.py'),'--candidate'],capture_output=True)
    (ROOT/'results/green_process.log').write_bytes(test.stdout+test.stderr);assert test.returncode==0,test.stderr[-1500:]
    scope=verify_method_scope();save(ROOT/'results/method_scope_verification.json',scope)
    conditions=[]
    for s in p['sources']:
        w=next(w for w in p['weights'] if w['seed']==s['seed']);assert sha(w['checkpoint'])==w['sha256'];model=YOLO(w['checkpoint']);names=model.names;del model
        for variant in p['variants']:conditions.append(run(p,s,names,variant))
    comparisons=[]
    for seed in [26,27,28]:
        a=load(ROOT/f'results/active_only_iou_seed{seed}/handoff_events.json');b=load(ROOT/f'results/allow_lost_iou_seed{seed}/handoff_events.json');m=evaluate_events(a,b,2.)
        comparisons.append({'seed':seed,'old_predictions':len(a),'new_predictions':len(b),'time_matched_prediction_pairs':m['temporally_matched'],
          'direction_disagreements':m['wrong_direction_matches'],'pairs':m['pairs'],
          'old_unpaired_events':[a[i] for i in m['unmatched_reference_indices']],
          'new_unpaired_events':[b[j] for j in m['unmatched_prediction_indices']],
          'prediction_comparison_not_reference_accuracy':True})
    save(ROOT/'results/summary.json',{'status':'ALL_SIX_PURE_IOU_VS_LOST_ELIGIBILITY_REPLAYS_COMPLETE',
      'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/lost_v1.json'),'scope':scope,
      'candidate_module_sha256':p['candidate_module_sha256'],'conditions':conditions,'prediction_comparisons':comparisons,
      'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy':None,'FPGA_execution_verified':False,'whole_goal_complete':False})
if __name__=='__main__':main()
