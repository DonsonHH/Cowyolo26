from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,importlib.util,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/control_v2'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mod(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
scanner=mod('unconfirmed_iou_independent_runs',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
geo=mod('unconfirmed_iou_independent_geometry',PROJECT/'detector_torso_pairs_20261029/tools/independent_geometry.py')
p=load(ROOT/'protocol/control_v2.json');s=load(OUT/'summary.json');gate=load(OUT/'all_baselines_gate.json')
assert s['protocol_sha256']==sha(ROOT/'protocol/control_v2.json') and s['counter_paths']==444 and s['tracker_updates']==217078
assert s['reused_successful_failed_run_baselines']==91 and len(gate['records'])==111 and gate['new_probe_updates_at_gate']==0
for row in load(ROOT/'delivery/protocol/failed_baselines_preserved.json'):
    assert sha(ROOT/'delivery'/row['file'])==row['sha256']
for row in p['port_files']:assert sha(PROJECT/'pynq_frontend_port_20261029'/row['file'])==row['sha256']
def optimum(reference,predictions):
    best=(-1,float('inf'));winners=[]
    def search(i,used,pairs,cost):
        nonlocal best,winners
        if i==len(reference):
            v=(len(pairs),cost)
            if v[0]>best[0] or v[0]==best[0] and cost<best[1]-1e-10:best=v;winners=[pairs]
            elif v[0]==best[0] and abs(cost-best[1])<=1e-10:winners.append(pairs)
            return
        search(i+1,used,pairs,cost)
        for j,r in enumerate(predictions):
            delta=abs(r['time_s']-reference[i]['time_s'])
            if j not in used and delta<=2:search(i+1,used|{j},pairs+[(i,j)],cost+delta)
    search(0,set(),[],0.)
    return best,winners
metrics=load(OUT/'metrics.json');paired=load(OUT/'paired_metrics.json');assert len(metrics)==476 and len(paired)==238
ticks=paths=spatial=metric_checks=formal=0;review_rows=[]
for c in p['caches']:
    for variant,file in [('baseline','baseline_trace.json.gz'),('unconfirmed_pure_IoU','unconfirmed_pure_IoU_trace.json.gz')]:
        trace=gz(OUT/c['id']/file);obs=trace['observations']
        assert [r['frame0'] for r in obs]==list(range(0,c['spec']['decode_end_exclusive'],c['stride']));ticks+=len(obs)
        post=defaultdict(list)
        for r in trace['post_tracker']:post[r['frame0']].append(r)
        W,H=c['spec']['width'],c['spec']['height'];lo,hi=c['spec']['perpendicular_ROI']
        for row in obs:
            positions={};ids=set()
            for r in post[row['frame0']]:
                tid=r['track_id']
                if tid is None:continue
                ids.add(tid);x,y,z,w=r['xyxy'];cx=(x+z)/(2*W);cy=(y+w)/(2*H)
                if lo<(cx if c['spec']['axis']=='y' else cy)<hi:positions[str(tid)]=cy if c['spec']['axis']=='y' else cx
                spatial+=1
            assert row['confirmed_positions']==positions and row['confirmed_IDs']==sorted(ids)
        for counter,admit in [('confirmed_only_events',False),('handoff_events',True)]:
            events,_=scanner.batch_events(obs,admit);assert events==trace[counter];paths+=1
            for window in c['windows']:
                chosen=[e for e in events if window['start']<=e['frame0']<window['end']]
                row=next(r for r in metrics if r['cache']==c['id'] and r['variant']==variant and r['window']==window['name'] and r['counter']==counter)
                assert row['events']==chosen and row['down']==sum(e['direction']=='A->B' for e in chosen) and row['up']==sum(e['direction']=='B->A' for e in chosen)
                if row['formal_event_metrics']:
                    best,winners=optimum(c['reference_events'],chosen);score=row['formal_event_metrics']
                    selected=sorted((e['reference_index'],e['prediction_index']) for e in score['pairs']);assert selected in winners and score['temporally_matched']==best[0]
                    correct=sum(c['reference_events'][a]['direction']==chosen[b]['direction'] for a,b in selected)
                    assert [score[k] for k in ['TP','FP','FN']]==[correct,len(chosen)-correct,len(c['reference_events'])-correct];formal+=1
                metric_checks+=1
    b=gz(OUT/c['id']/'baseline_trace.json.gz')
    old=ROOT/'delivery/results/control'/c['id']/'baseline_trace.json.gz'
    if old.exists():assert gz(old)==b
for r in paired:
    rows=[next(x for x in metrics if all(x[k]==r[k] for k in ['cache','window','counter']) and x['variant']==variant) for variant in ['baseline','unconfirmed_pure_IoU']]
    assert [r['baseline_down'],r['control_down'],r['baseline_up'],r['control_up']]==[rows[0]['down'],rows[1]['down'],rows[0]['up'],rows[1]['up']]
assert ticks==217078 and paths==444 and metric_checks==476
focus=OUT/'new_O8_original_s5';baseline=next(r for r in load(focus/'baseline_focus.json') if r['frame0']==9550)
control=next(r for r in load(focus/'unconfirmed_pure_IoU_focus.json') if r['frame0']==9550)
assert len(baseline['detection_scores'])==len(control['detection_scores'])==1 and baseline['detection_scores']==control['detection_scores']
score=baseline['detection_scores'][0];pure=baseline['pure_IoU_cost'][0][0];fused=baseline['fused_cost'][0][0]
assert abs(fused-(1-(1-pure)*score))<1e-7 and 1-score>.7 and pure<.7<fused
assert baseline['unconfirmed_IDs'][0] in baseline['removed_IDs_after_stage'] and control['unconfirmed_IDs'][0] in control['activated_IDs_after_stage']
assert baseline['detection_xyxy']==control['detection_xyxy'] and baseline['pure_IoU_cost']==control['pure_IoU_cost']
references=load(PROJECT/'mosaic_event_diagnosis_20261030/input/reference_boxes.json')
control_trace=gz(focus/'unconfirmed_pure_IoU_trace.json.gz')
correspondences=[]
for e in control_trace['handoff_events']:
    if e['direction']!='A->B':continue
    refs=[r for r in references if r['frame0']==e['frame0']]
    candidates=[r for r in control_trace['post_tracker'] if r['frame0']==e['frame0'] and r['track_id'] is not None]
    matrix=[[geo.iou(r['xyxy'],c['xyxy']) for c in candidates] for r in refs]
    best,_=geo.independent_best_matching(matrix,.5)
    target=[(i,j) for i,r in enumerate(refs) for j,c in enumerate(candidates) if r['reference_track_id']==103 and c['track_id']==e['track_id'] and matrix[i][j]>=.5]
    if target:
        # The event-time frame contains one target with high overlap; verify it
        # belongs to a cardinality/IoU-optimal correspondence independently.
        i,j=target[0]
        other_refs=[x for k,x in enumerate(refs) if k!=i];other_preds=[x for k,x in enumerate(candidates) if k!=j]
        rest,_=geo.independent_best_matching([[geo.iou(r['xyxy'],c['xyxy']) for c in other_preds] for r in other_refs],.5)
        assert 1+rest[0]==best[0] and abs(matrix[i][j]+rest[1]-best[1])<1e-8
        correspondences.append((e,refs[i],candidates[j]))
assert len(correspondences)==1
event,ref,box=correspondences[0]
focus_result={'status':'SINGLE_UNCONFIRMED_COST_INTERVENTION_CONTINUES_TENTATIVE_TRACK_AND_RESTORES_REFERENCE103_EVENT',
    'frame0':9550,'score':score,'pure_IoU_cost':pure,'fused_cost':fused,'best_possible_fused_cost':1-score,'threshold':.7,
    'baseline_tentative_ID':baseline['unconfirmed_IDs'][0],'control_tentative_ID':control['unconfirmed_IDs'][0],
    'baseline_removed_ID':baseline['removed_IDs_after_stage'],'control_activated_ID':control['activated_IDs_after_stage'],
    'restored_event':event,'event_reference103_IoU':geo.iou(ref['xyxy'],box['xyxy']),'reference_is_independent_GT':False}
original=next(r for r in paired if r['cache']=='native_original_seed26' and r['counter']=='handoff_events');assert original['baseline_down']==original['control_down']==12
changed=[r for r in paired if (r['baseline_down'],r['baseline_up'])!=(r['control_down'],r['control_up'])]
newtarget=next(r for r in paired if r['cache']=='new_O8_original_s5' and r['counter']=='handoff_events');assert [newtarget['baseline_down'],newtarget['control_down']]==[10,11]
result={'status':'ALL444_COUNTER_PATHS217078_TICKS476_SCOPE_METRICS_AND_FOCUS_COST_INTERVENTION_RECOMPUTED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'cache_count':111,'tracker_conditions':222,'counter_observation_ticks':ticks,
    'counter_paths':paths,'scope_metric_rows':metric_checks,'formal_publisher_score_rows':formal,'post_tracker_spatial_rows_checked':spatial,
    'paired_scope_rows':238,'changed_scope_rows':len(changed),'baseline_reused_without_rerun':91,
    'hardware_Toros_shared_ID_allocator_original_order_retained':True,'no_ID_relabeling_or_tolerance_relaxation':True,
    'new_O8_original_counts':[10,11],'old_O8_original_counts':[11,11],'legacy_confirmed12_retained':True,
    'focus':focus_result,'new_model_forwards':0,'new_training_updates':0,'actual_board_executed_in_this_control':False,
    'adopted_for_deployment':False,'new_independent_test':False,'whole_goal_complete':False}
f=ROOT/'results/independent_verification.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
