"""Read-only instrumentation; require exact whole-history outputs afterwards."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,sys
import numpy as np,torch,ultralytics
from ultralytics import YOLO
import ultralytics.trackers.byte_tracker as byte_module
from ultralytics.trackers.byte_tracker import BYTETracker,TrackState
from ultralytics.trackers.utils import matching
from ultralytics.utils import YAML,IterableSimpleNamespace
from reproduce import ROOT,load,save,sha,read,normal,guards,step,ZoneCounter,ConfirmationHandoffCounter

def describe(t):
    return {'track_ID':int(t.track_id),'state':int(t.state),'activated':bool(t.is_activated),
            'xyxy':np.asarray(t.xyxy).tolist(),'score':float(t.score),'index_in_threshold_subset':int(t.idx),
            'last_update_step':int(t.frame_id),'start_step':int(t.start_frame)}
def pools(tracker):
    return {name:[describe(t) for t in getattr(tracker,name)] for name in ['tracked_stracks','lost_stracks','removed_stracks']}

class TraceTracker(BYTETracker):
    def __init__(self,args):super().__init__(args);self.record=None;self.stage=None
    def _first_association(self,pool,detections,activated,refind):
        self.stage='first'
        if self.record is not None:
            dists=self.get_dists(pool,detections);ious=1-matching.iou_distance(pool,detections)
            self.record['first']={'tracks':[describe(t) for t in pool],'high_detections':[describe(t) for t in detections],
                                  'IoUs':ious.tolist(),'costs':dists.tolist(),'threshold':float(self.args.match_thresh)}
        result=super()._first_association(pool,detections,activated,refind)
        if self.record is not None:
            self.record['first']['unmatched_track_indices']=[int(i) for i in result[0]]
            self.record['first']['unmatched_detection_indices']=[int(i) for i in result[1]]
        return result
    def _second_association(self,pool,u_track,detections,activated,refind,lost):
        self.stage='second'
        if self.record is not None:
            eligible=[pool[i] for i in u_track if pool[i].state==TrackState.Tracked]
            eligible_cost=matching.iou_distance(eligible,detections)
            if self.args.fuse_score:eligible_cost=matching.fuse_score(eligible_cost,detections)
            target=next((t for t in pool if t.track_id==19),None)
            diag_iou=1-matching.iou_distance([target],detections) if target is not None else np.empty((0,len(detections)))
            diag_cost=matching.fuse_score(1-diag_iou,detections) if self.args.fuse_score else 1-diag_iou
            self.record['second']={'eligible_tracks':[describe(t) for t in eligible],'low_detections':[describe(t) for t in detections],
                                   'costs':eligible_cost.tolist(),'threshold':.5,'target_eligible':any(t.track_id==19 for t in eligible),
                                   'diagnostic_target_geometry':describe(target) if target is not None else None,
                                   'diagnostic_target_IoUs':diag_iou.tolist(),'diagnostic_target_costs':diag_cost.tolist()}
        return super()._second_association(pool,u_track,detections,activated,refind,lost)
    def _apply_match(self,track,det,activated,refind):
        if self.record is not None:
            self.record['applied_matches'].append({'stage':self.stage,'track':describe(track),'detection':describe(det)})
        return super()._apply_match(track,det,activated,refind)
    def _unconfirmed_association(self,unconfirmed,u_detection,detections,activated,removed):
        self.stage='unconfirmed'
        if self.record is not None:
            selected=[detections[i] for i in u_detection]
            self.record['unconfirmed']={'tracks':[describe(t) for t in unconfirmed],'leftover_high_detections':[describe(t) for t in selected],
                                        'costs':self.get_dists(unconfirmed,selected).tolist(),'threshold':.7}
        return super()._unconfirmed_association(unconfirmed,u_detection,detections,activated,removed)
    def _init_new_tracks(self,u_detection,detections,activated,refind=None):
        before={id(t) for t in activated}
        output=super()._init_new_tracks(u_detection,detections,activated,refind)
        if self.record is not None:self.record['newly_initialized']=[describe(t) for t in activated if id(t) not in before]
        return output

def main():
    p=load(ROOT/'protocol/reproduce_v1.json');q=load(ROOT/'protocol/association_probe_v1.json');guards(p)
    assert q['full_replay_protocol_sha256']==sha(ROOT/'protocol/reproduce_v1.json')
    source=Path(p['source_folder'])
    for r in p['source_files']:assert sha(source/r['name'])==r['sha256']
    assert load(ROOT/'results/reproduce/summary.json')['status']=='SEED26_FULL_RAW_TRACK_OBSERVATION_AND_TWO_EVENT_PATHS_REPLAY_EXACT'
    for index in [1,2]:assert load(ROOT/f'results/reproduce/red_signal_{index}.json')['status']=='FAIL_EXPECTED_BASELINE_GAP'
    model=YOLO(p['weights']['checkpoint']);names=model.names;del model;cow=next(k for k,v in names.items() if v=='cow')
    raw=defaultdict(list)
    for r in read(source/'raw_detector_boxes.csv'):
        raw[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence']),cow])
    args=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml');tracker=TraceTracker(IterableSimpleNamespace(**args))
    base=ZoneCounter(**p['counter']);counter=ConfirmationHandoffCounter(**p['counter']);image=np.zeros((1440,2560,3),np.uint8)
    original_merge=byte_module.merge_track_pools
    def recording_merge(tracker,activated,refind,lost,removed):
        record=tracker.record
        if record is not None:
            record['before_merge']=pools(tracker)
            record['merge_inputs']={name:[describe(t) for t in values] for name,values in [('activated',activated),('refound',refind),('lost',lost),('removed',removed)]}
        result=original_merge(tracker,activated,refind,lost,removed)
        if record is not None:record['after_merge']=pools(tracker)
        return result
    records=[];post=[];tracks=[];observations=[];events=[];base_events=[]
    try:
        byte_module.merge_track_pools=recording_merge
        for frame in range(0,10125,5):
            tracker.record={'frame0':frame,'raw_native_boxes':raw[frame],'before_update':pools(tracker),'applied_matches':[]} if frame in q['short_replay_frames'] else None
            a,b,c,d=step(tracker,base,counter,frame,np.asarray(raw[frame],np.float32).reshape(-1,6),names,image)
            post.extend(a);tracks.extend(b);observations.append(c);base_events.extend(d[0]);events.extend(d[1])
            if tracker.record is not None:
                tracker.record.update(full_image_confirmed_IDs=c['confirmed_IDs'],confirmed_ROI_positions=c['confirmed_positions'],
                    tentative_ROI_positions=c['tentative_positions'],accepted_history=c['accepted_history'],
                    target_counter_state=vars(counter.counters[19].states[19]).copy(),
                    fragment_counter_state=vars(counter.counters[23].states[23]).copy() if 23 in counter.counters and 23 in counter.counters[23].states else None,
                    emitted_events=d[1]);records.append(tracker.record)
    finally:byte_module.merge_track_pools=original_merge
    assert post==normal(read(source/'post_tracker_boxes.csv')) and tracks==normal(read(source/'tracks.csv'))
    assert json.loads(json.dumps(observations))==load(source/'observations.json')
    assert base_events==load(source/'confirmed_only_events_all_history.json') and events==load(source/'handoff_events_all_history.json')
    out=ROOT/'results/association';out.mkdir(exist_ok=False);save(out/'trace.json',records)
    sources=out/'installed_sources';sources.mkdir()
    captured=[]
    for relative in ['trackers/byte_tracker.py','trackers/utils/stracks.py','trackers/utils/matching.py','cfg/trackers/bytetrack.yaml']:
        file=Path(ultralytics.__path__[0])/relative;target=sources/Path(relative).name;target.write_bytes(file.read_bytes())
        captured.append({'relative_installed_path':relative,'file':target.relative_to(ROOT).as_posix(),'sha256':sha(target)})
    summary={'status':'FULL_OUTPUT_PRESERVING_SIX_UPDATE_ASSOCIATION_TRACE_CAPTURED','job_id':os.environ['SLURM_JOB_ID'],
             'probe_protocol_sha256':sha(ROOT/'protocol/association_probe_v1.json'),'full_replay_ticks':2025,'probe_updates':len(records),
             'all_post_tracks_tentative_history_and_events_exact':True,'handoff_down_unchanged':len(events),
             'installed_sources':captured,'new_detector_forwards':0,'new_training_updates':0,'formal_scores_computed':False,
             'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    manifest=[]
    for folder in ['results','protocol','input','tools']:
        for f in sorted((ROOT/folder).rglob('*')):
            if f.is_file():manifest.append({'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)})
    save(ROOT/'delivery_manifest.json',{'files':manifest})
    import tarfile
    archive=ROOT/'gap_diagnostic_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for row in manifest:tf.add(ROOT/row['file'],arcname=row['file'])
        tf.add(ROOT/'delivery_manifest.json',arcname='delivery_manifest.json')
    print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'files':len(manifest)+1}),flush=True)
if __name__=='__main__':main()
