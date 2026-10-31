"""Verify all condition coordinates, counter events, reference scores and overlaps."""
from pathlib import Path
from collections import defaultdict,Counter
import ast,csv,hashlib,importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def number_rows(rows):
    return [{k:None if v in ['',None] else int(v) if k in ['frame0','track_id'] else float(v) for k,v in r.items()} for r in rows]
def overlap(a,b):
    dx=max(0.,min(a['x2'],b['x2'])-max(a['x1'],b['x1']));dy=max(0.,min(a['y2'],b['y2'])-max(a['y1'],b['y1']))
    aa=max(0.,a['x2']-a['x1'])*max(0.,a['y2']-a['y1']);bb=max(0.,b['x2']-b['x1'])*max(0.,b['y2']-b['y1'])
    return dx*dy/(aa+bb-dx*dy+1e-7)
def main():
    p=load(ROOT/'protocol/regression_v1.json');dest=ROOT/'delivery';summary=load(dest/'results/summary.json')
    assert sha(ROOT/'protocol/regression_v1.json')==sha(dest/'protocol/regression_v1.json')==summary['protocol_sha256']
    for row in load(dest/'delivery_manifest.json')['files']:
        assert (dest/row['file']).stat().st_size==row['bytes'] and sha(dest/row['file'])==row['sha256']
    for name,digest in p['input_modules'].items():assert sha(ROOT/'input'/name)==sha(dest/'input'/name)==digest
    for source in p['sources']:
        for f in source['files']:assert Path(f['local']).stat().st_size==f['bytes'] and sha(Path(f['local']))==f['sha256']
    current=ast.parse((ROOT/'input/firststage_tracker.py').read_text(encoding='utf-8'))
    prior=ast.parse((PROJECT/'long_video_track_gap_20261029/tools/firststage_control.py').read_text(encoding='utf-8'))
    a=next(n for n in current.body if isinstance(n,ast.ClassDef));b=next(n for n in prior.body if isinstance(n,ast.ClassDef) and n.name==a.name)
    assert ast.dump(a,include_attributes=False)==ast.dump(b,include_attributes=False)
    sys.path.insert(0,str(PROJECT/'long_video_fixed_replay_20261029/input'))
    scanner=module('native_independent_counter_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
    reference_tools=module('publisher_independent_reference_tools',PROJECT/'external_method_regression_20261028/tools/verify_local.py')
    reference=reference_tools.reference_from_publisher(ROOT/'input/publisher_gt_original.txt')
    assert reference==load(ROOT/'input/publisher_event_summary.json')['events'] and len(reference)==6
    gate=load(dest/'results/baseline_gate.json');assert len(gate['conditions'])==9
    assert gate['status']=='NINE_FIXED_CACHES_ORIGINAL_OUTPUTS_EXACT_BEFORE_ANY_CANDIDATE'
    checked=[];scored=[];all_ticks=0;all_centers=0;all_pairs=0;overlap_candidates=0;admissions=0
    for condition in summary['conditions']:
        source=next(s for s in p['sources'] if s['name']==condition['source']);folder=dest/'results'/condition['name']
        assert condition==load(folder/'summary.json') and condition['checkpoint_sha256']==source['weights']['sha256']
        obs=load(folder/'observations.json');post=number_rows(read(folder/'post_tracker_boxes.csv'));tracks=number_rows(read(folder/'tracks.csv'))
        assert [r['frame0'] for r in obs]==list(range(0,source['history_end_frame0_exclusive'],source['stride']))
        by_post=defaultdict(list);by_tracks=defaultdict(list);calculated_overlaps=[]
        for row in post:by_post[row['frame0']].append(row)
        for row in tracks:by_tracks[row['frame0']].append(row)
        for row in obs:
            f=row['frame0'];assert row['time_s']==f/source['fps'];positions={};active=set();selected=[];selected_tracks=[]
            for box in by_post[f]:
                assert box['time_s']==f/source['fps'];tid=box['track_id']
                if tid is None:continue
                active.add(tid)
                cx=(box['x1']+box['x2'])/(2*source['width']);cy=(box['y1']+box['y2'])/(2*source['height'])
                low,high=source['perpendicular_ROI'];perpendicular=cx if source['axis']=='y' else cy
                if not low<perpendicular<high:continue
                axis=cy if source['axis']=='y' else cx;positions[str(tid)]=axis;selected.append(box)
                selected_tracks.append({**box,'axis_position':axis} if source['axis']=='y' else
                    {'frame0':f,'time_s':f/source['fps'],'track_id':tid,'axis_position':axis,'cy_norm':cy})
            assert positions==row['confirmed_positions'] and sorted(active)==row['confirmed_IDs'] and selected_tracks==by_tracks[f]
            all_centers+=len(selected_tracks)
            for i,a in enumerate(selected):
                for b in selected[i+1:]:
                    all_pairs+=1;value=overlap(a,b)
                    if value>=.5:
                        calculated_overlaps.append({'frame0':f,'IDa':a['track_id'],'IDb':b['track_id'],'IoU':value,
                            'box_a':[a[k] for k in ['x1','y1','x2','y2']],'box_b':[b[k] for k in ['x1','y1','x2','y2']]})
        assert calculated_overlaps==load(folder/'ROI_overlap_candidates.json')
        assert len(calculated_overlaps)==condition['ROI_overlap_pairs_by_tick']
        assert len({r['frame0'] for r in calculated_overlaps})==condition['ROI_ticks_with_overlap_candidate']
        overlap_candidates+=len(calculated_overlaps)
        events_by_counter={}
        for name,admit,file in [('confirmed_only',False,'confirmed_only_events_all_history.json'),('confirmation_handoff',True,'handoff_events_all_history.json')]:
            events,accepted=scanner.batch_events(obs,admit);assert events==load(folder/file);events_by_counter[name]=events
            if admit:
                expected=sorted((r for o in obs for r in o['accepted_history']),key=lambda r:(r['confirmation_time_s'],r['track_id']))
                assert accepted==expected;admissions+=len(accepted)
            for window in source['windows']:
                a,b=window['start_frame0'],window['end_frame0_exclusive'];selected=[e for e in events if a<=e['frame0']<b]
                w=next(w for w in condition['window_counters'] if w['window']==window['name'] and w['counter']==name)
                assert w['events']==selected and w['down']==sum(e['direction']=='A->B' for e in selected) and w['up']==sum(e['direction']=='B->A' for e in selected)
                if source['scene']=='original_clip':assert w['human_down_total']==12 and w['absolute_down_total_error']==abs(w['down']-12)
                if source['formal_event_scoring_allowed']:
                    assert source['reference_events']==reference;metric=w['formal_event_metrics']
                    n,error,pairs=reference_tools.exhaustive(reference,selected)
                    tp=sum(reference[i]['direction']==selected[j]['direction'] for i,j in pairs)
                    assert (n,tp,len(selected)-tp,len(reference)-tp)==(metric['temporally_matched'],metric['TP'],metric['FP'],metric['FN'])
                    assert abs(error-sum(r['time_error_s'] for r in metric['pairs']))<1e-10
                    assert len({r['reference_index'] for r in metric['pairs']})==len(metric['pairs'])==len({r['prediction_index'] for r in metric['pairs']})
                    for pair in metric['pairs']:
                        r,e=reference[pair['reference_index']],selected[pair['prediction_index']]
                        assert abs(r['time_s']-e['time_s'])==pair['time_error_s']<=2
                        assert pair['direction_correct']==(r['direction']==e['direction'])
                    assert metric['precision']==(tp/len(selected) if selected else None)
                    assert metric['recall']==tp/6 and metric['f1']==2*tp/(len(selected)+6)
                    scored.append({'condition':condition['name'],'counter':name,'TP':tp,'FP':len(selected)-tp,'FN':6-tp,
                                   'pair_error_sum_s':error,'unmatched_reference_indices':metric['unmatched_reference_indices']})
                else:assert w['formal_event_metrics'] is None
        assert condition['ROI_rows']==len(tracks) and condition['post_tracker_rows']==len(post) and condition['observation_ticks']==len(obs)
        assert condition['all_history_down']==sum(e['direction']=='A->B' for e in events_by_counter['confirmation_handoff'])
        assert condition['all_history_up']==sum(e['direction']=='B->A' for e in events_by_counter['confirmation_handoff'])
        if condition['variant']=='original_fused':assert condition['baseline_checks']['both_counter_event_paths_exact'] is True and condition['name'] in gate['conditions']
        checked.append({'condition':condition['name'],'scene':source['scene'],'model':source['model'],'variant':condition['variant'],
                        'observation_ticks':len(obs),'ROI_centers':len(tracks),'counter_paths':2,'window_counters':condition['window_counters'],
                        'overlap_candidate_rows':len(calculated_overlaps),'overlap_candidate_ticks':len({r['frame0'] for r in calculated_overlaps})})
        all_ticks+=len(obs)
    assert len(checked)==18 and all_ticks==summary['total_tracker_updates']==31166 and len(scored)==8
    for pair in summary['paired_results']:
        old=next(r for r in summary['conditions'] if r['source']==pair['source'] and r['variant']=='original_fused')
        new=next(r for r in summary['conditions'] if r['source']==pair['source'] and r['variant']=='firststage_pure_IoU')
        assert pair['ROI_overlap_ticks_before_after']==[old['ROI_ticks_with_overlap_candidate'],new['ROI_ticks_with_overlap_candidate']]
        for a,b,diff in zip(old['window_counters'],new['window_counters'],pair['window_differences']):
            signature=lambda es:Counter((e['frame0'],e['direction']) for e in es)
            x,y=signature(a['events']),signature(b['events'])
            assert diff['time_direction_multiset_added']==[list(e) for e in (y-x).elements()]
            assert diff['time_direction_multiset_removed']==[list(e) for e in (x-y).elements()]
            assert diff['before_down_up']==[a['down'],a['up']] and diff['after_down_up']==[b['down'],b['up']]
    record={'status':'ALL18_CONDITIONS_36_COUNTER_PATHS_8_REFERENCE_SCORES_AND_OVERLAPS_INDEPENDENTLY_VERIFIED',
            'tracker_runs':18,'counter_paths':36,'observation_ticks':all_ticks,'counter_interface_ticks':all_ticks*2,
            'native_ROI_centers_verified':all_centers,'ROI_box_pair_IoUs_verified':all_pairs,'ROI_overlap_candidate_rows':overlap_candidates,
            'tentative_observations_admitted':admissions,'Toros_reference_rows':1775,'Toros_reference_events':6,'reference_scored_paths':scored,
            'condition_checks':checked,'baseline_gate_conditions':9,'same_candidate_method_AST_verified':True,
            'new_detector_forwards':0,'new_training_updates':0,'new_long_reference_scores_computed':False,'candidate_adopted':False,
            'FPGA_execution_verified':False,'whole_goal_complete':False}
    out=ROOT/'results/independent_verification.json';assert not out.exists();out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['condition_checks','reference_scored_paths']}))
    print(json.dumps(scored))
if __name__=='__main__':main()
