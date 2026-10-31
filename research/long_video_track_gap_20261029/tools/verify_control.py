"""Independently check all native coordinates and four complete counter paths."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    folder=ROOT/'control_delivery';rows=load(folder/'control_delivery_manifest.json')['files']
    for r in rows:assert (folder/r['file']).stat().st_size==r['bytes'] and sha(folder/r['file'])==r['sha256']
    for name in ['tools/firststage_control.py','protocol/firststage_control_v1.json']:
        assert sha(ROOT/name)==sha(folder/name)
    p=load(ROOT/'protocol/firststage_control_v1.json');assert p['candidate_adoption_allowed'] is False
    sys.path.insert(0,str(PROJECT/'long_video_fixed_replay_20261029/input'))
    spec=importlib.util.spec_from_file_location('frozen_counter_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    dest=folder/'results/firststage_control';summary=load(dest/'summary.json');assert summary['candidate_adopted'] is False
    results=[];event_signatures=[];centers=0
    for name in ['original_fused','firststage_pure_IoU']:
        case=dest/name;obs=load(case/'observations.json');post=load(case/'post_tracker_boxes.json');tracks=load(case/'native_ROI_tracks.json')
        assert [r['frame0'] for r in obs]==list(range(0,10125,5))
        by_post=defaultdict(list);by_track=defaultdict(list)
        for r in post:by_post[r['frame0']].append(r)
        for r in tracks:by_track[r['frame0']].append(r)
        for r in obs:
            frame=r['frame0'];assert r['time_s']==frame/25;positions={};selected=[];active=set()
            for row in by_post[frame]:
                tid=row['track_id']
                if tid is None:continue
                active.add(tid)
                if .34<(row['x1']+row['x2'])/5120<.75:
                    cy=(row['y1']+row['y2'])/2880;positions[str(tid)]=cy;selected.append({**row,'axis_position':cy})
            assert positions==r['confirmed_positions'] and sorted(active)==r['confirmed_IDs']
            assert selected==by_track[frame];centers+=len(selected)
        for admit,event_file in [(False,'confirmed_only_events.json'),(True,'handoff_events.json')]:
            independent,accepted=module.batch_events(obs,admit);stored=load(case/event_file);assert independent==stored
            if admit:
                original=sorted((a for r in obs for a in r['accepted_history']),key=lambda a:(a['confirmation_time_s'],a['track_id']))
                assert original==accepted
        events=load(case/'handoff_events.json');event_signatures.append(Counter((e['frame0'],e['direction']) for e in events))
        stored=load(case/'summary.json');assert stored['observations']==2025 and stored['ROI_rows']==len(tracks) and stored['post_tracker_rows']==len(post)
        assert stored['handoff_down']==stored['confirmed_only_down']==len(events)
        for window in stored['window_counters']:
            a,b={'group_passage':(2375,4375),'late_single':(5000,5625),'person_control':(9625,10125)}[window['window']]
            es=load(case/('handoff_events.json' if window['counter']=='confirmation_handoff' else 'confirmed_only_events.json'))
            selected=[e for e in es if a<=e['frame0']<b];assert selected==window['events']
            assert window['down']==sum(e['direction']=='A->B' for e in selected) and window['up']==sum(e['direction']=='B->A' for e in selected)==0
        if name=='original_fused':
            original=PROJECT/'long_video_fixed_replay_20261029/delivery/results/seed26'
            assert obs==load(original/'observations.json') and events==load(original/'handoff_events_all_history.json')
        results.append({'mode':name,'native_ROI_rows':len(tracks),'post_tracker_rows':len(post),'observations':2025,'down_events':len(events),'up_events':0})
    assert [r['down_events'] for r in results]==[11,12]
    short=load(dest/'short_paired_replay.json');assert [r['recovered_original_ID_in_B'] for r in short]==[False,True]
    assert [r['original_ID19_A_to_B_emitted'] for r in short]==[False,True]
    for name,row in zip(['original_fused','firststage_pure_IoU'],short):
        assert row['mode']==name
        target=[(r['frame0'],r['confirmed_positions'].get('19')) for r in row['observations']]
        assert all(pos is None for frame,pos in target if frame in [2650,2655,2660])
        if name=='firststage_pure_IoU':
            assert all(pos>.6 for frame,pos in target if frame in [2665,2670,2675])
            assert row['handoff_events']==[{'time_s':107.,'track_id':19,'direction':'A->B','frame0':2675}]
            assert [r['ID19_state']['streak'] for r in row['states']][-3:]==[1,2,3]
        else:assert row['handoff_events']==[]
    added=list((event_signatures[1]-event_signatures[0]).elements());removed=list((event_signatures[0]-event_signatures[1]).elements())
    assert added==[(2675,'A->B'),(3840,'A->B')] and removed==[(3845,'A->B')]
    result={'status':'FIRSTSTAGE_CONTROL_FOUR_COUNTER_PATHS_AND_SNAPSHOT_RECOVERY_INDEPENDENTLY_VERIFIED',
            'manifest_files':len(rows),'whole_history_conditions':2,'counter_paths':4,'observation_ticks':4050,
            'counter_interface_update_ticks':8100,'native_ROI_centers_verified':centers,'results':results,
            'baseline_short_signal':'RED','candidate_short_signal':'GREEN','candidate_ID19_event_frame0':2675,
            'prediction_time_multiset_added':added,'prediction_time_multiset_removed':removed,
            'identity_numbers_not_matched_across_variants':True,'counterfactual_predictions_are_not_independent_GT':True,
            'candidate_adopted':False,'old_confirmed12_clip_regression_pending':True,'other_seed_regression_pending':True,
            'new_detector_forwards':0,'new_training_updates':0,'formal_scores_computed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/control_independent_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
if __name__=='__main__':main()
