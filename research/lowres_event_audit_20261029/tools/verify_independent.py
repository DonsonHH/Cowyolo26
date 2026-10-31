from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import json,gzip,hashlib,sys,importlib.util,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
geometry=module('event_audit_independent_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
scanner=module('event_audit_independent_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
p=load(ROOT/'protocol/audit_v1.json');s=load(ROOT/'results/summary.json');assert s['protocol_sha256']==sha(ROOT/'protocol/audit_v1.json')
reference=defaultdict(list)
for r in load(ROOT/'input/reference_boxes.json'):reference[r['frame0']].append(r)
for rows in reference.values():rows.sort(key=lambda r:r['reference_track_id'])
assert sum(map(len,reference.values()))==581
checks=assignments=oracles=rows_checked=0;fulltable=[];admission_checks=0
for cache in p['caches']:
    raw={r['frame0']:r['predictions'] for r in loadgz(cache['raw_file'])};trace=loadgz(cache['trace_file']);post=defaultdict(list)
    for r in trace['post_tracker']:
        if r['track_id'] is not None:post[r['frame0']].append(r)
    for threshold in p['IoU_thresholds']:
        folder=ROOT/'results'/cache['condition']/('iou'+str(threshold).replace('.',''));case=load(folder/'case.json');ledger=loadgz(folder/'frame_correspondence.json.gz')
        assert len(ledger)==581;byframe=defaultdict(list)
        for row in ledger:byframe[row['frame0']].append(row)
        positions={mode:defaultdict(dict) for mode in p['oracles']}
        for frame,refs in reference.items():
            ledgerrows=byframe[frame];assert [r['reference_track_id'] for r in ledgerrows]==[r['reference_track_id'] for r in refs]
            for kind,predictions,indexkey,ioukey in [('raw',raw[frame],'raw_prediction_index','raw_IoU'),('post',post[frame],'post_prediction_index','post_IoU')]:
                matrix=[[geometry.iou(ref['xyxy'],pred['xyxy']) for pred in predictions] for ref in refs]
                best,ties=geometry.independent_best_matching(matrix,threshold)
                chosen=[(i,r[indexkey]) for i,r in enumerate(ledgerrows) if r[indexkey] is not None]
                assert len(chosen)==best[0] and len({j for i,j in chosen})==len(chosen)
                assert abs(sum(matrix[i][j] for i,j in chosen)-best[1])<1e-8
                for i,j in chosen:assert ledgerrows[i][ioukey]==matrix[i][j]>=threshold
                assignments+=1
            for ref,row in zip(refs,ledgerrows):
                tid=ref['reference_track_id'];assert row['reference_box']==ref['xyxy'] and row['reference_axis_position']==ref['axis_position']
                if row['raw_prediction_index'] is not None:
                    pred=raw[frame][row['raw_prediction_index']];assert pred['xyxy']==row['raw_box'] and pred['confidence']==row['raw_confidence']
                    a,b,c,d=pred['xyxy'];x=(a+c)/(2*2560);y=(b+d)/(2*1440)
                    assert row['raw_axis_position']==y and row['raw_center_eligible_ROI']==(.34<x<.75)
                    positions[p['oracles'][0]][frame][str(tid)]=ref['axis_position']
                    if .34<x<.75:positions[p['oracles'][1]][frame][str(tid)]=y
                if row['post_prediction_index'] is not None:
                    pred=post[frame][row['post_prediction_index']];assert pred['xyxy']==row['post_box'] and pred['track_id']==row['post_track_id']
                    a,b,c,d=pred['xyxy'];x=(a+c)/(2*2560);y=(b+d)/(2*1440)
                    assert row['post_axis_position']==y and row['post_center_eligible_ROI']==(.34<x<.75)
                    if .34<x<.75:positions[p['oracles'][2]][frame][str(tid)]=y
                rows_checked+=1
        for admission in case['post_admission_checks']:
            admission_checks+=1
            if not admission['admitted_to_oracle']:continue
            previous=admission['observation_frame0'];tid=str(admission['reference_track_id']);f=admission['confirmation_frame0']
            current=next(r for r in byframe[f] if str(r['reference_track_id'])==tid)
            assert current['post_track_id']==admission['candidate_track_id'] and tid not in positions[p['oracles'][2]][previous]
            prior=next(r for r in byframe[previous] if str(r['reference_track_id'])==tid)
            assert prior['raw_prediction_index'] is not None and abs(prior['raw_axis_position']-admission['actual_axis_position'])<=.0001
            positions[p['oracles'][2]][previous][tid]=admission['actual_axis_position']
        streams=loadgz(folder/'oracle_observations.json.gz')
        for mode in p['oracles']:
            observations=streams[mode];assert len(observations)==2175
            for row in observations:
                assert row['confirmed_positions']==positions[mode][row['frame0']] and row['confirmed_IDs']==sorted(int(v) for v in row['confirmed_positions'])
            events,_=scanner.batch_events(observations,False);assert events==case['oracle_events'][mode];oracles+=1
            assert case['oracle_down_counts'][mode]==sum(e['direction']=='A->B' for e in events)
        buckets=Counter()
        for row in case['tracks']:
            tid=row['reference_track_id'];frames=[r for r in ledger if r['reference_track_id']==tid]
            assert row['raw_correspondence_samples']==sum(r['raw_prediction_index'] is not None for r in frames)
            assert row['post_correspondence_samples']==sum(r['post_prediction_index'] is not None for r in frames)
            assert row['post_ID_frequencies']=={str(k):v for k,v in Counter(r['post_track_id'] for r in frames if r['post_track_id'] is not None).items()}
            for mode in p['oracles']:
                for zone in ['A','B']:
                    samples=[r['frame0'] for r in streams[mode] if str(tid) in r['confirmed_positions'] and (r['confirmed_positions'][str(tid)]<.4 if zone=='A' else r['confirmed_positions'][str(tid)]>.6)]
                    runs=[]
                    for f in samples:
                        if not runs or f!=runs[-1][-1]+5:runs.append([f])
                        else:runs[-1].append(f)
                    assert row['longest_stable_region_runs'][mode][zone]==max(map(len,runs),default=0)
                assert row['oracle_down_events'][mode]==sum(e['track_id']==tid and e['direction']=='A->B' for e in case['oracle_events'][mode])
            buckets[row['diagnostic_bucket']]+=1
        assert dict(buckets)==case['per_track_diagnostic_buckets']
        actual=[e for e in trace['handoff_events'] if 8912<=e['frame0']<=10873]
        assert case['actual_global_down_count']==sum(e['direction']=='A->B' for e in actual)
        for e in case['actual_events_direct_correspondence']:
            assert {k:v for k,v in e.items() if k not in ['reference_track_id','direct_event_frame_spatial_match']} in actual
            candidates=[r for r in byframe[e['frame0']] if r['post_track_id']==e['track_id']]
            assert len(candidates)==1 and candidates[0]['reference_track_id']==e['reference_track_id']
        checks+=1
        fulltable.append({'condition':cache['condition'],'size':cache['size'],'seed':cache['seed'],'threshold':threshold,'actual_down':case['actual_global_down_count'],
            'presence_reference_center_down':case['oracle_down_counts'][p['oracles'][0]],'raw_center_assisted_down':case['oracle_down_counts'][p['oracles'][1]],
            'post_center_assisted_down':case['oracle_down_counts'][p['oracles'][2]],'actual_events_unmapped':case['actual_unmapped_event_count'],
            'reference_not_independent_truth':True})
assert checks==54 and oracles==162 and rows_checked==31374 and assignments==38664
primary05=load(ROOT/'results/S192_rot90_seed26/iou05/case.json');primary03=load(ROOT/'results/S192_rot90_seed26/iou03/case.json')
assert primary05['actual_global_down_count']==6 and primary05['oracle_down_counts']==primary03['oracle_down_counts']
miss=[r for r in primary05['tracks'] if r['actual_direct_corresponding_down_events']==0]
assert len(miss)==6 and all(r['oracle_down_events'][p['oracles'][0]]==0 for r in miss)
nonmonotone=[r for r in fulltable if r['actual_down']>r['raw_center_assisted_down'] or r['actual_down']>r['post_center_assisted_down']]
result={'status':'ALL54_REFERENCE_CONDITIONED_CASES38664_MATCHINGS_AND162_ORACLE_PATHS_INDEPENDENTLY_VERIFIED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'cases':checks,'reference_case_rows':rows_checked,'matching_problems':assignments,
 'independent_counter_oracle_paths':oracles,'post_admission_checks':admission_checks,'primary_direct_count':6,
 'primary_6_unmapped_reference_tracks_fail_presence_oracle':True,'primary_iou05_iou03_oracle_counts_same':True,
 'primary_oracle_down_counts':primary05['oracle_down_counts'],'actual_larger_than_some_oracle_case_count':len(nonmonotone),
 'oracles_are_not_monotonic_upper_bounds':True,'diagnostic_reference_is_independent_GT':False,
 'new_network_forwards':0,'new_training_updates':0,'board_actions':0,'whole_goal_complete':False}
file=ROOT/'results/independent_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
with (ROOT/'results/all_conditions.csv').open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(fulltable[0]));w.writeheader();w.writerows(fulltable)
print(json.dumps(result))
