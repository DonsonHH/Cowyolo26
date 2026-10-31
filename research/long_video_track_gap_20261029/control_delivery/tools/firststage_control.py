"""One-factor firststage cost control; never modifies the installed package."""
from pathlib import Path
from collections import defaultdict
import copy,csv,json,os,pickle,sys,time
import numpy as np,torch,ultralytics
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.trackers.basetrack import BaseTrack
from ultralytics.trackers.utils import matching
from ultralytics.utils import YAML,IterableSimpleNamespace
from reproduce import ROOT,load,save,sha,read,normal,guards,step,ZoneCounter,ConfirmationHandoffCounter

class FirstStagePureIoUTracker(BYTETracker):
    def _first_association(self,pool,detections,activated,refind):
        costs=matching.iou_distance(pool,detections)
        matches,u_track,u_detection=matching.linear_assignment(costs,thresh=self.args.match_thresh)
        self._apply_matches(matches,pool,detections,activated,refind)
        return u_track,u_detection

def snapshot_run(data,p,control):
    # Includes BaseTrack's class counter, which is outside the pickled instance.
    snapshot=pickle.loads(data);tracker=snapshot['tracker'];BaseTrack._count=snapshot['base_track_count']
    if control:tracker.__class__=FirstStagePureIoUTracker
    base=snapshot['base'];counter=snapshot['counter'];image=np.zeros((1440,2560,3),np.uint8)
    obs=[];posts=[];events=[];baseline_events=[];states=[]
    for frame,array in snapshot['frames']:
        a,b,c,d=step(tracker,base,counter,frame,array,snapshot['names'],image)
        if not control:assert json.loads(json.dumps(c))==snapshot['expected_observations'][str(frame)]
        posts.extend(a);obs.append(c);baseline_events.extend(d[0]);events.extend(d[1])
        states.append({'frame0':frame,'ID19_state':vars(counter.counters[19].states[19]).copy(),
                       'ID23_state':vars(counter.counters[23].states[23]).copy() if 23 in counter.counters and 23 in counter.counters[23].states else None})
    target=p['target_ID']
    return {'mode':'firststage_pure_IoU' if control else 'original_fused','observations':obs,'post_tracker_boxes':posts,
            'confirmed_only_events':baseline_events,'handoff_events':events,'states':states,
            'recovered_original_ID_in_B':any(target in r['confirmed_positions'] and r['confirmed_positions'][target]>.6 for r in obs),
            'original_ID19_A_to_B_emitted':any(e['track_id']==target and e['direction']=='A->B' for e in events)}

def full_run(p,names,control):
    source=Path(p['source_folder']);cow=next(k for k,v in names.items() if v=='cow');raw=defaultdict(list)
    for row in read(source/'raw_detector_boxes.csv'):
        raw[int(row['frame'])].append([*[float(row[k]) for k in ['x1','y1','x2','y2']],float(row['confidence']),cow])
    cfg=YAML.load(ultralytics.__path__[0]+'/cfg/trackers/bytetrack.yaml')
    cls=FirstStagePureIoUTracker if control else BYTETracker;tracker=cls(IterableSimpleNamespace(**cfg))
    base=ZoneCounter(**p['counter']);counter=ConfirmationHandoffCounter(**p['counter'])
    image=np.zeros((1440,2560,3),np.uint8);obs=[];post=[];tracks=[];base_events=[];events=[]
    for frame in range(0,10125,5):
        a,b,c,d=step(tracker,base,counter,frame,np.asarray(raw[frame],np.float32).reshape(-1,6),names,image)
        post.extend(a);tracks.extend(b);obs.append(c);base_events.extend(d[0]);events.extend(d[1])
    if not control:
        assert post==normal(read(source/'post_tracker_boxes.csv')) and tracks==normal(read(source/'tracks.csv'))
        assert json.loads(json.dumps(obs))==load(source/'observations.json')
        assert base_events==load(source/'confirmed_only_events_all_history.json') and events==load(source/'handoff_events_all_history.json')
    windows=[('group_passage',2375,4375),('late_single',5000,5625),('person_control',9625,10125)]
    summaries=[]
    for name,a,b in windows:
        for counter_name,es in [('confirmed_only',base_events),('confirmation_handoff',events)]:
            selected=[e for e in es if a<=e['frame0']<b]
            summaries.append({'window':name,'counter':counter_name,'down':sum(e['direction']=='A->B' for e in selected),
                              'up':sum(e['direction']=='B->A' for e in selected),'events':selected})
    return {'mode':'firststage_pure_IoU' if control else 'original_fused','observations':obs,'post_tracker_boxes':post,
            'native_ROI_tracks':tracks,'confirmed_only_events':base_events,'handoff_events':events,
            'summary':{'observations':len(obs),'post_tracker_rows':len(post),'ROI_rows':len(tracks),
                       'confirmed_only_down':sum(e['direction']=='A->B' for e in base_events),
                       'handoff_down':sum(e['direction']=='A->B' for e in events),'window_counters':summaries,
                       'baseline_exact':not control,'new_detector_forwards':0,'new_training_updates':0}}

def main():
    p=load(ROOT/'protocol/reproduce_v1.json');q=load(ROOT/'protocol/firststage_control_v1.json');guards(p)
    assert sha(ROOT/'tools/firststage_control.py')==q['implementation_sha256']
    for row in p['source_files']:assert sha(Path(p['source_folder'])/row['name'])==row['sha256']
    snapshot=ROOT/'results/reproduce/before_02650.pkl';record=load(ROOT/'results/reproduce/snapshot_record.json')
    assert sha(snapshot)==record['sha256'];data=snapshot.read_bytes();out=ROOT/'results/firststage_control';out.mkdir(exist_ok=False)
    short=[snapshot_run(data,p,control) for control in [False,True]]
    assert short[0]['recovered_original_ID_in_B'] is False and short[0]['original_ID19_A_to_B_emitted'] is False
    save(out/'short_paired_replay.json',short)
    names=pickle.loads(data)['names'];full=[]
    for control in [False,True]:
        row=full_run(p,names,control);mode=row['mode'];dest=out/mode;dest.mkdir()
        for key in ['observations','post_tracker_boxes','native_ROI_tracks','confirmed_only_events','handoff_events','summary']:
            save(dest/(key+'.json'),row[key])
        full.append({'mode':mode,**row['summary']})
    summary={'status':'ONE_FACTOR_FIRSTSTAGE_COST_SNAPSHOT_AND_FULL_LONG_VIDEO_CONTROL_COMPLETE',
             'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/firststage_control_v1.json'),
             'short_snapshot_cases':[{'mode':r['mode'],'ID19_recovered_in_B':r['recovered_original_ID_in_B'],
                                      'ID19_event_emitted':r['original_ID19_A_to_B_emitted'],'events':r['handoff_events']} for r in short],
             'full_video_conditions':full,'old_confirmed12_clip_or_other_models_replayed_in_this_control':False,
             'candidate_adopted':False,'new_detector_forwards':0,'new_training_updates':0,'formal_scores_computed':False,
             'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    manifest=[]
    for folder in ['results','protocol','input','tools']:
        for f in sorted((ROOT/folder).rglob('*')):
            if f.is_file():manifest.append({'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)})
    save(ROOT/'control_delivery_manifest.json',{'files':manifest})
    import tarfile
    archive=ROOT/'firststage_control_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for row in manifest:tf.add(ROOT/row['file'],arcname=row['file'])
        tf.add(ROOT/'control_delivery_manifest.json',arcname='control_delivery_manifest.json')
    print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'files':len(manifest)+1}),flush=True)
if __name__=='__main__':main()
