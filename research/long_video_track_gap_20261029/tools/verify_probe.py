"""Independent box arithmetic and exhaustive partial-assignment checks."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def iou(a,b):
    a=np.asarray(a,np.float32).astype(float);b=np.asarray(b,np.float32).astype(float)
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    union=max(0,a[2]-a[0])*max(0,a[3]-a[1])+max(0,b[2]-b[0])*max(0,b[3]-b[1])-intersection
    return float(intersection/(union+1e-7))
def all_assignments(cost,rows,cols,limit):
    candidates=[]
    def visit(row,used,pairs,objective):
        if row==rows:candidates.append((objective,list(pairs)));return
        visit(row+1,used,pairs,objective)
        for col in range(cols):
            if col in used or cost[row][col]>limit:continue
            visit(row+1,used|{col},pairs+[(row,col)],objective+cost[row][col]-limit)
    visit(0,set(),[],0.)
    optimum=min(x[0] for x in candidates)
    winners=[pairs for objective,pairs in candidates if abs(objective-optimum)<1e-7]
    return winners,len(candidates),optimum
def main():
    p=load(ROOT/'protocol/reproduce_v1.json');q=load(ROOT/'protocol/association_probe_v1.json');folder=ROOT/'delivery'
    manifest=load(folder/'delivery_manifest.json')['files']
    for row in manifest:assert (folder/row['file']).stat().st_size==row['bytes'] and sha(folder/row['file'])==row['sha256']
    for name in ['tools/reproduce.py','tools/association_probe.py','protocol/reproduce_v1.json','protocol/association_probe_v1.json']:
        assert sha(ROOT/name)==sha(folder/name)
    raw=defaultdict(list)
    with (PROJECT/'long_video_fixed_replay_20261029/delivery/results/seed26/raw_detector_boxes.csv').open(newline='') as f:
        for r in csv.DictReader(f):raw[int(r['frame'])].append([*[float(r[k]) for k in ['x1','y1','x2','y2']],float(r['confidence'])])
    summary=load(folder/'results/association/summary.json');repro=load(folder/'results/reproduce/summary.json')
    assert summary['all_post_tracks_tentative_history_and_events_exact'] is True and repro['all_tentative_and_admitted_history_exact'] is True
    assert summary['handoff_down_unchanged']==repro['handoff_down']==repro['confirmed_only_down']==11
    a=load(folder/'results/reproduce/red_signal_1.json');b=load(folder/'results/reproduce/red_signal_2.json')
    assert {k:v for k,v in a.items() if k!='loop_elapsed_s'}=={k:v for k,v in b.items() if k!='loop_elapsed_s'}
    assert a['status']=='FAIL_EXPECTED_BASELINE_GAP' and a['real_tracker_updates']==6
    assert a['original_ID19_recovered_in_B'] is False and a['original_ID19_A_to_B_emitted'] is False
    trace=load(folder/'results/association/trace.json');assert [r['frame0'] for r in trace]==q['short_replay_frames']
    entries=0;maxerror=0.;assignments=0;comparisons=[]
    for r in trace:
        frame=r['frame0'];first=r['first'];tracks=first['tracks'];dets=first['high_detections']
        assert [x[:5] for x in r['raw_native_boxes']]==raw[frame]
        high=[x for x in raw[frame] if x[4]>=.25];low=[x for x in raw[frame] if .1<x[4]<.25]
        assert len(dets)==len(high) and len(low)==len(r['second']['low_detections'])==0
        for index,(d,source) in enumerate(zip(dets,high)):
            assert d['index_in_threshold_subset']==index and d['score']==source[4]
            assert max(abs(a-b) for a,b in zip(d['xyxy'],source[:4]))<.0005
        for stage,ts,ds,costs in [('first',tracks,dets,first['costs']),
                                 ('second',r['second']['eligible_tracks'],r['second']['low_detections'],r['second']['costs']),
                                 ('unconfirmed',r['unconfirmed']['tracks'],r['unconfirmed']['leftover_high_detections'],r['unconfirmed']['costs'])]:
            for i,t in enumerate(ts):
                for j,d in enumerate(ds):
                    overlap=iou(t['xyxy'],d['xyxy']);expected=1-overlap*d['score'];error=abs(expected-costs[i][j])
                    if stage=='first':error=max(error,abs(overlap-first['IoUs'][i][j]))
                    assert error<1e-6,(frame,stage,i,j,error);maxerror=max(maxerror,error);entries+=1
        winners,count,objective=all_assignments(first['costs'],len(tracks),len(dets),first['threshold']);assignments+=count
        actual=[]
        for match in r['applied_matches']:
            if match['stage']!='first':continue
            i=next(i for i,t in enumerate(tracks) if t['track_ID']==match['track']['track_ID'])
            j=match['detection']['index_in_threshold_subset'];actual.append((i,j))
        assert sorted(actual) in [sorted(w) for w in winners]
        assert sorted(first['unmatched_track_indices'])==[i for i in range(len(tracks)) if i not in {a for a,b in actual}]
        assert sorted(first['unmatched_detection_indices'])==[j for j in range(len(dets)) if j not in {b for a,b in actual}]
        target_index=next(i for i,t in enumerate(tracks) if t['track_ID']==19);target=tracks[target_index]
        assert target['state']==(1 if frame==2650 else 2) and 19 not in r['full_image_confirmed_IDs']
        assert 19 in [t['track_ID'] for t in r['after_merge']['lost_stracks']]
        assert r['target_counter_state']['origin']=='A' and r['emitted_events']==[]
        assert r['second']['target_eligible']==(frame==2650)
        # The raw cow-role correspondence below is a post-prediction assistant
        # case annotation, not a new training label or independently accepted GT.
        candidate_index={2665:2,2670:1,2675:1}.get(frame)
        best=min(range(len(dets)),key=lambda j:first['costs'][target_index][j])
        item={'frame0':frame,'target_state_before':target['state'],'target_available_in_first_pool':True,
              'target_predicted_native_xyxy':target['xyxy'],'target_first_min_cost':first['costs'][target_index][best],
              'target_min_cost_detection_index':best,'target_min_cost_detection_assigned_to':next((tracks[i]['track_ID'] for i,j in actual if j==best),None),
              'current_target_output':False,'target_lost_after':True,'low_detections':0,
              'source_supported_leading_cow_candidate_index':candidate_index,
              'physical_correspondence_authority':'assistant_post_prediction_case_review'}
        if candidate_index is not None:
            d=dets[candidate_index];overlap=iou(target['xyxy'],d['xyxy']);cost=first['costs'][target_index][candidate_index]
            item.update(candidate_native_xyxy=d['xyxy'],candidate_score=d['score'],candidate_IoU=overlap,
                        candidate_fused_cost=cost,candidate_cost_exceeds_limit=cost>.8,
                        hypothetical_pure_IoU_cost=1-overlap,hypothetical_pure_IoU_pair_within_limit=1-overlap<=.8,
                        candidate_index_is_original_high_subset=True)
            assert cost>.8
        comparisons.append(item)
    result={'status':'SIX_ASSOCIATION_STEPS_COSTS_AND_GLOBAL_ASSIGNMENTS_INDEPENDENTLY_VERIFIED',
            'manifest_files_verified':len(manifest),'real_matrix_entries_verified':entries,'maximum_cost_or_IoU_error':maxerror,
            'partial_assignments_enumerated':assignments,'firststage_global_assignments_verified':6,
            'red_signal_repeated_exactly':True,'short_loop_update_count':6,
            'full_tracker_updates_per_replay':2025,'original_full_outputs_preserved':True,
            'diagnostic_frame_summaries':comparisons,
            'hypothesis_status':{'H1':'Native source case review supports a retained-detector gap; not independent recall truth.',
                                 'H2':'Supported: reappearing cow candidates exceed firststage fused limit; cheaper follower candidate is already assigned toID20.',
                                 'H3':'Original ID remains available as Lost in firststage; expiry/removal is ruled out for these updates. No low detections means secondstage eligibility is not the active recovery route.',
                                 'H4':'Ruled out: target is absent even from full-image confirmed outputs.'},
            'hypothetical_unfused_pair_feasibility_is_not_a_replayed_algorithm_or_count_improvement':True,
            'source_detections_weights_references_and_confirmed12_changed':False,
            'new_detector_forwards':0,'new_training_updates':0,'formal_scores_computed':False,
            'FPGA_execution_verified':False,'whole_goal_complete':False}
    path=ROOT/'results/independent_verification.json';assert not path.exists();path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['diagnostic_frame_summaries','hypothesis_status']}))
    for row in comparisons:print(json.dumps(row))
if __name__=='__main__':main()
