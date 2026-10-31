from pathlib import Path
from collections import defaultdict,Counter
import csv,hashlib,json,os,socket,subprocess,sys
import numpy as np,torch,ultralytics
from ultralytics import YOLO
from ultralytics.engine.results import Results
from ultralytics.trackers.byte_tracker import BYTETracker,TrackState
from ultralytics.trackers.utils import matching
from ultralytics.utils import YAML,IterableSimpleNamespace
from secondstage_tracker import SecondStageIoUTracker,verify_method_scope
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/secondstage_iou_20261028')
sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
from event_metrics import evaluate_events
FIELDS=['source_frame','time_s','track_id','confidence','x1','y1','x2','y2','axis_position']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def read(p):return list(csv.DictReader(Path(p).open(newline='')))
def save(p,value):Path(p).write_text(json.dumps(value,indent=2))
def normal(rows):return [{k:int(v) if k in ['source_frame','track_id'] else float(v) for k,v in r.items()} for r in rows]
def writecsv(path,rows,fields=FIELDS):
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
class AuditMixin:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.decisions=[];self.second_calls=0;self.active_second=None
        self.pure_iou=isinstance(self,SecondStageIoUTracker)
    def _second_association(self,pool,unmatched,low,activated,refind,lost):
        self.second_calls+=1;eligible=[pool[i] for i in unmatched if pool[i].state==TrackState.Tracked]
        if eligible and low:
            raw=matching.iou_distance(eligible,low)
            cost=raw if self.pure_iou else matching.fuse_score(raw,low) if self.args.fuse_score else raw
            d={'source_frame':(self.frame_id-1)*5,'eligible_IDs':[int(t.track_id) for t in eligible],
               'eligible_xyxy':[np.asarray(t.xyxy).tolist() for t in eligible],
               'low_detections':[{'stage_local_index':int(d.idx),'xyxy':np.asarray(d.xyxy).tolist(),'confidence':float(d.score)} for d in low],
               'IoUs':(1-raw).tolist(),'costs':cost.tolist(),'threshold':.5,'score_fusion_in_secondstage':not self.pure_iou and bool(self.args.fuse_score),
               'lost_IDs_excluded':[int(pool[i].track_id) for i in unmatched if pool[i].state!=TrackState.Tracked],
               'applied_pairs':[]}
            self.decisions.append(d);self.active_second=d
        else:self.active_second=None
        try:return super()._second_association(pool,unmatched,low,activated,refind,lost)
        finally:self.active_second=None
    def _apply_match(self,track,det,activated,refind):
        if self.active_second is not None:
            d=self.active_second;ri=d['eligible_IDs'].index(int(track.track_id));ci=int(det.idx)
            assert 0<=ci<len(d['low_detections'])
            d['applied_pairs'].append({'row_index':ri,'low_stage_index':ci,'track_ID':int(track.track_id),
               'cost':d['costs'][ri][ci],'confidence':float(det.score)})
        return super()._apply_match(track,det,activated,refind)
class AuditedOriginal(AuditMixin,BYTETracker):pass
class AuditedIoU(AuditMixin,SecondStageIoUTracker):pass

def run(p,source,names,variant):
    seed=source['seed'];name=f'{variant}_seed{seed}';dest=ROOT/'results'/name;dest.mkdir(exist_ok=False)
    folder=Path(source['remote_folder']);raw=defaultdict(list);cow=next(k for k,v in names.items() if v=='cow')
    for r in read(folder/'pretracker_boxes.csv'):raw[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),cow])
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');assert cfg['fuse_score'] is True and cfg['track_buffer']==30
    tracker=(AuditedOriginal if variant=='installed_baseline' else AuditedIoU)(IterableSimpleNamespace(**cfg))
    ordinary=ZoneCounter(**p['counter']);handoff=ConfirmationHandoffCounter(**p['counter']);rows=[];history=[];allrows=[];events0=[];events1=[];observations=[]
    image=np.zeros((1440,2560,3),np.uint8)
    for frame in range(0,10874,5):
        result=Results(orig_img=image,path='cached',names=names,boxes=torch.from_numpy(np.asarray(raw[frame],np.float32).reshape(-1,6)))
        output=tracker.update(result.boxes.cpu().numpy(),result.orig_img,feats=None)
        if len(output):result=result[output[:,-1].astype(int)];result.update(boxes=torch.as_tensor(output[:,:-1]))
        b=result.boxes;ids=b.id.int().cpu().tolist() if b.id is not None else [None]*len(b);active={i for i in ids if i is not None};positions={};tentative={}
        for box,confidence,tid in zip(b.xyxy.cpu().tolist(),b.conf.cpu().tolist(),ids):
            x1,y1,x2,y2=box
            allrows.append({'source_frame':frame,'track_id':tid,'confidence':confidence,'x1':x1,'y1':y1,'x2':x2,'y2':y2})
            if tid is None or not .34<(x1+x2)/5120<.75:continue
            row=dict(zip(FIELDS,[frame,frame/25,tid,confidence,x1,y1,x2,y2,(y1+y2)/2880]));positions[tid]=row['axis_position']
            (rows if frame>=8912 else history).append(row)
        for t in tracker.tracked_stracks:
            if not t.is_activated:
                x1,y1,x2,y2=np.asarray(t.xyxy,np.float32).astype(float)
                if .34<(x1+x2)/5120<.75:tentative[int(t.track_id)]=(y1+y2)/2880
        for output,target in [(ordinary.update(frame/25,positions),events0),(handoff.update(frame/25,positions,tentative,active),events1)]:
            for e in output:
                e['source_frame']=frame
                if frame>=8912:target.append(e)
        observations.append({'source_frame':frame,'confirmed_positions':positions,'confirmed_IDs':sorted(active),'tentative_positions':tentative,
            'accepted_history':[{**r,'observation_source_frame':round(r['observation_time_s']*25),'confirmation_source_frame':frame} for r in handoff.last_acceptances]})
    assert tracker.second_calls==2175
    if variant=='installed_baseline':
        assert normal(rows)==normal(read(folder/'source_tracks.csv')) and normal(history)==normal(read(folder/'source_warmup_tracks.csv'))
        assert events0==load(folder/'source_events.json')
        assert events1==load(Path(p['prior_handoff_paths'][str(seed)])/'handoff_events.json')
        assert not any(d['applied_pairs'] for d in tracker.decisions)
    writecsv(dest/'source_tracks.csv',rows);writecsv(dest/'source_warmup_tracks.csv',history)
    writecsv(dest/'all_posttracker_boxes.csv',allrows,['source_frame','track_id','confidence','x1','y1','x2','y2'])
    for filename,value in [('confirmed_only_events.json',events0),('handoff_events.json',events1),('observations.json',observations),('secondstage_decisions.json',tracker.decisions)]:save(dest/filename,value)
    record={'name':name,'variant':variant,'seed':seed,'predicted_down':sum(e['direction']=='A->B' for e in events1),
      'predicted_up':sum(e['direction']=='B->A' for e in events1),'confirmed_only_down':sum(e['direction']=='A->B' for e in events0),
      'confirmed_only_up':sum(e['direction']=='B->A' for e in events0),'ROI_track_IDs':len({r['track_id'] for r in rows}),
      'ROI_track_rows':len(rows),'history_track_rows':len(history),'ROI_tracked_frames':len({r['source_frame'] for r in rows}),
      'nonempty_secondstage_decisions':len(tracker.decisions),'applied_low_stage_matches_all_history':sum(len(d['applied_pairs']) for d in tracker.decisions),
      'applied_low_stage_matches_in_scope':sum(len(d['applied_pairs']) for d in tracker.decisions if d['source_frame']>=8912),
      'effective_default_config_unchanged':cfg,'firststage_score_fusion_enabled':True,'secondstage_score_fusion_enabled':variant=='installed_baseline',
      'secondstage_threshold':.5,'lost_secondstage_eligibility_changed':False,'baseline_exact_regression':variant=='installed_baseline',
      'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy':None,'board_execution':False}
    save(dest/'summary.json',record);print(json.dumps(record),flush=True);return record
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';torch.set_num_threads(2)
    p=load(ROOT/'protocol/secondstage_v1.json');binding=load(ROOT/'protocol/input_binding.json')
    assert binding['protocol_sha256']==sha(ROOT/'protocol/secondstage_v1.json') and ultralytics.__version__=='8.4.63'
    assert sha(ROOT/'tools/secondstage_tracker.py')==p['candidate_module_sha256']
    for name,checksum in p['input_modules'].items():assert sha(ROOT/'input'/name)==checksum
    source_files={'installed_track.py':'trackers/track.py','installed_byte_tracker.py':'trackers/byte_tracker.py','installed_bytetrack.yaml':'cfg/trackers/bytetrack.yaml'}
    for f in p['installed_source']:assert sha(Path(ultralytics.__path__[0])/source_files[f['file']])==f['sha256']
    assert sha(Path(ultralytics.__path__[0])/'trackers/utils/matching.py')==p['matching_source_sha256']
    for source in p['sources']:
        for f in source['files']:assert sha(Path(source['remote_folder'])/f['name'])==f['sha256']
    for r in binding['prior_handoff_files']:
        for f in r['files']:assert sha(Path(p['prior_handoff_paths'][str(r['seed'])])/f['name'])==f['sha256']
    test=subprocess.run([sys.executable,str(ROOT/'tools/test_real_gate.py')],capture_output=True)
    (ROOT/'results/candidate_test_process.log').write_bytes(test.stdout+test.stderr);assert test.returncode==0,test.stderr[-2000:]
    scope=verify_method_scope();save(ROOT/'results/method_scope_verification.json',scope)
    conditions=[]
    for source in p['sources']:
        w=next(w for w in p['weights'] if w['seed']==source['seed']);assert sha(w['checkpoint'])==w['sha256']
        model=YOLO(w['checkpoint']);names=model.names;del model
        for variant in p['baseline_and_candidate_order']:conditions.append(run(p,source,names,variant))
    comparisons=[]
    for seed in [26,27,28]:
        old=load(ROOT/f'results/installed_baseline_seed{seed}/handoff_events.json');new=load(ROOT/f'results/secondstage_iou_seed{seed}/handoff_events.json')
        metrics=evaluate_events(old,new,tolerance_s=2.)
        comparisons.append({'seed':seed,'old_predictions':len(old),'new_predictions':len(new),
          'time_matched_prediction_pairs':metrics['temporally_matched'],'direction_disagreements_in_pairs':metrics['wrong_direction_matches'],
          'pairs':metrics['pairs'],'old_unpaired_events':[old[i] for i in metrics['unmatched_reference_indices']],
          'new_unpaired_events':[new[i] for i in metrics['unmatched_prediction_indices']],
          'comparison_is_prediction_vs_prediction_not_source_accuracy':True})
    save(ROOT/'results/summary.json',{'status':'SIX_FROZEN_INPUT_REPLAYS_SECONDSTAGE_SINGLE_FACTOR_CONTROL_COMPLETE',
      'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/secondstage_v1.json'),
      'input_binding_sha256':sha(ROOT/'protocol/input_binding.json'),'candidate_module_sha256':p['candidate_module_sha256'],
      'scope':scope,'conditions':conditions,'prediction_comparisons':comparisons,'main_counter':'unchangedconfirmationhandoff',
      'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy':None,'FPGA_execution_verified':False,'whole_goal_complete':False})
if __name__=='__main__':main()
