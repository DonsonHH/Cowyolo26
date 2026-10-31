from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
from PIL import Image
import numpy as np
import json,hashlib,math,csv
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;STUDY=ROOT/'delivery/results/study'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def metrics(rows):
    known=[r for r in rows if r['identity'] in gallery_ids];unknown=[r for r in rows if r['identity'] not in gallery_ids]
    c=sum(r['accepted'] and r['predicted_id']==r['identity'] for r in known);w=sum(r['accepted'] and r['predicted_id']!=r['identity'] for r in known)
    u=sum(not r['accepted'] for r in known);f=sum(r['accepted'] for r in unknown);top=sum(r['predicted_id']==r['identity'] for r in known)
    return {'known_queries':len(known),'unknown_queries':len(unknown),'known_correct_accepted_C':c,'known_wrong_accepted_W':w,
            'known_rejected_U':u,'unknown_false_accepts':f,'known_closed_top1_correct':top,'known_correct_accepted_rate':c/len(known),
            'unknown_false_acceptance_rate':f/len(unknown)}
def independent_calibration(rows):
    values=sorted({r['similarity'] for r in rows});values.append(float(np.nextafter(values[-1],np.inf)))
    best_key=None;best=None;feasible=0
    for t in values:
        p=[{**r,'accepted':r['similarity']>=t} for r in rows];m=metrics(p)
        if m['unknown_false_accepts']>1:continue
        feasible+=1;key=(m['known_correct_accepted_C'],-m['known_wrong_accepted_W'],t)
        if best_key is None or key>best_key:best_key=key;best=(t,m)
    assert best is not None;return best[0],best[1],feasible
def local(row):return Path(row['local_path'])
protocol=load(ROOT/'protocol/study_v1.json');index=load(STUDY/'input_index.json');frozen=load(STUDY/'selection_frozen.json');summary=load(STUDY/'summary.json')
assert summary['protocol_sha256']==sha(ROOT/'protocol/study_v1.json') and summary['frozen_selection_sha256']==sha(STUDY/'selection_frozen.json')
access=load(STUDY/'access_log.json');prefix=load(STUDY/'accesses_at_freeze.json')
assert len(access)==182 and len(prefix)==80 and access[:80]==prefix
assert {r['group'] for r in prefix}=={'validation_gallery','validation_query'} and not any(r['evaluation_gate_open'] for r in prefix)
assert all(r['evaluation_gate_open'] for r in access[80:]) and frozen['evaluation_image_accesses']==0
for group in ['validation_gallery','validation_query','evaluation_gallery','evaluation_query','real_event_query']:
    assert {r['path'] for r in index[group]}=={r['path'] for r in access if r['group']==group}
batchlog=load(STUDY/'forward_batches.json');assert sum(r['batch_images'] for r in batchlog)==3640
assert sum(r['batch_images'] for r in batchlog if not r['evaluation_gate_open'])==1600
assert sum(r['batch_images'] for r in batchlog if r['evaluation_gate_open'])==2040
tensor_log=load(STUDY/'tensor_log.json');image_log=load(STUDY/'image_transform_log.json');assert len(tensor_log)==len(image_log)==3640
previous_tensor=load(PROJECT/'crossdate_gallery_20261029/delivery/results/study_v2/tensor_hashes.json')
previous_index={(r['condition'],r['group'],r['query_id']):r['tensor_sha256'] for r in previous_tensor}
for r in tensor_log:
    if r['rule']=='P0_original' and r['group'] in ['evaluation_gallery','evaluation_query','real_event_query']:
        qid=None if r['group']=='evaluation_gallery' else r['query_id']
        group={'evaluation_gallery':'new_Aug19_gallery','evaluation_query':'labelled_curated_query','real_event_query':'real_event_query'}[r['group']]
        assert r['tensor_sha256']==previous_index[(r['condition'],group,qid)] if group!='new_Aug19_gallery' else True
# Gallery tensors are keyed by path in older log (no query ID there).
oldgallery=[r for r in previous_tensor if r['group']=='new_Aug19_gallery']
currentgallery=[r for r in tensor_log if r['rule']=='P0_original' and r['group']=='evaluation_gallery']
assert len(oldgallery)==len(currentgallery)==150
assert all(a['tensor_sha256']==b['tensor_sha256'] for a,b in zip(oldgallery,currentgallery))
pixel_cache={};transform_checked={};source_index={(group,r['query_id']):r for group,rows in index.items() for r in rows}
for log in image_log:
    key=(log['group'],log['query_id'],log['rule'])
    if key not in transform_checked:
        row=source_index[(log['group'],log['query_id'])];file=local(row);assert sha(file)==log['source_sha256']
        if str(file) not in pixel_cache:
            with Image.open(file) as im:im.load();pixel_cache[str(file)]=np.asarray(im.convert('RGB'))
        pixels=pixel_cache[str(file)];h,w=pixels.shape[:2];rule=next(r for r in protocol['crop_rules'] if r['name']==log['rule'])
        applies=rule['apply_to']=='gallery_and_query' or rule['apply_to']=='query_only' and log['group'].endswith('query')
        fw=rule['center_width'] if applies else 1.;fh=rule['center_height'] if applies else 1.
        box=[math.floor((1-fw)*w/2),math.floor((1-fh)*h/2),math.ceil((1+fw)*w/2),math.ceil((1+fh)*h/2)]
        expected=pixels[box[1]:box[3],box[0]:box[2]]
        rotation=180 if applies and rule['rotation_CCW']==180 else 0
        if rotation:expected=np.rot90(expected,2)
        digest=hashlib.sha256(expected.tobytes()).hexdigest();transform_checked[key]={'pixel':digest,'box':box,'rotation':rotation,'size':[expected.shape[1],expected.shape[0]]}
    expected=transform_checked[key]
    assert log['transformed_RGB_pixel_sha256']==expected['pixel'] and log['crop_box']==expected['box'] and log['rotation_CCW']==expected['rotation'] and log['output_dimensions']==expected['size']
assert len(transform_checked)==728
counts={'dot_products':0,'identity_scores':0,'unique_retrieval_rows':0,'threshold_decisions':0}
max_dot=0.;max_identity=0.;maximum_unit_norm_error=0.;all_metrics=[];false_cases=[];real_outcomes=[];val_selection=[];rule_outcomes=[]
for condition in protocol['conditions']:
    options=[]
    for rule in protocol['crop_rules']:
        directory=STUDY/(condition['name']+'__'+rule['name']);valsummary=load(directory/'validation_summary.json')
        for stage in ['validation','evaluation']:
            z=np.load(directory/(stage+'_embeddings.npz'))
            grows=index[stage+'_gallery'];gallery_ids=sorted({r['identity'] for r in grows})
            assert len(gallery_ids)==(5 if stage=='validation' else 6)
            for name in z.files:maximum_unit_norm_error=max(maximum_unit_norm_error,float(np.max(np.abs(np.linalg.norm(z[name].astype(float),axis=1)-1))))
            groups=[(stage+'_query','query',stage)]
            if stage=='evaluation':groups.append(('real_event_query','real_event_query','real_event'))
            for qgroup,zkey,fileprefix in groups:
                qrows=index[qgroup];base=load(directory/(fileprefix+'_original_fixed_predictions.json'))
                assert len(base)==len(qrows)
                for qi,(r,q) in enumerate(zip(base,z[zkey].astype(float))):
                    assert r['query_id']==qrows[qi]['query_id']
                    dots=[math.fsum(float(a)*float(b) for a,b in zip(q,g)) for g in z['gallery'].astype(float)]
                    max_dot=max(max_dot,max(abs(a-b) for a,b in zip(dots,r['gallery_image_cosines'])));counts['dot_products']+=len(dots)
                    scores={identity:max(dots[i] for i,g in enumerate(grows) if g['identity']==identity) for identity in gallery_ids}
                    max_identity=max(max_identity,max(abs(scores[identity]-r['identity_scores'][identity]) for identity in gallery_ids))
                    counts['identity_scores']+=len(gallery_ids);winner=max(gallery_ids,key=lambda identity:scores[identity])
                    assert winner==r['predicted_id'] and abs(scores[winner]-r['similarity'])<1e-12;counts['unique_retrieval_rows']+=1
                thresholds={'original_fixed':condition['threshold'],'validation_calibrated':valsummary['calibration']['threshold']}
                if stage=='validation':
                    calculated_t,vm,feasible=independent_calibration(base)
                    assert calculated_t==thresholds['validation_calibrated']
                    assert vm['known_correct_accepted_C']==valsummary['calibration']['calibration_known_correct_accepted']
                    val_selection.append({'condition':condition['name'],'rule':rule['name'],'independent_threshold':calculated_t,'feasible_thresholds':feasible,
                        'C':vm['known_correct_accepted_C'],'W':vm['known_wrong_accepted_W'],'F':vm['unknown_false_accepts'],'Top1':vm['known_closed_top1_correct']})
                    if rule['selection_eligible']:options.append((vm['known_correct_accepted_C'],-vm['known_wrong_accepted_W'],vm['known_closed_top1_correct'],-protocol['crop_rules'].index(rule),rule['name'],calculated_t))
                for method,t in thresholds.items():
                    rows=load(directory/(fileprefix+'_'+method+'_predictions.json'));assert len(rows)==len(base)
                    for j,(r,b) in enumerate(zip(rows,base)):
                        assert r['query_id']==b['query_id'] and r['predicted_id']==b['predicted_id'] and r['similarity']==b['similarity'] and r['threshold']==t and r['accepted']==(b['similarity']>=t)
                        counts['threshold_decisions']+=1
                        if fileprefix=='real_event':
                            assert r['identity_reference'] is None and r['verified_identity'] is False
                            real_outcomes.append({'condition':condition['name'],'rule':rule['name'],'threshold_method':method,'query_id':r['query_id'],
                                'predicted_id':r['predicted_id'],'similarity':r['similarity'],'threshold':t,'accepted':r['accepted'],'verified_identity':False})
                        else:
                            assert r['is_known']==(r['identity'] in gallery_ids)
                            if r['accepted'] and (not r['is_known'] or r['identity']!=r['predicted_id']):
                                gi=max((i for i,g in enumerate(grows) if g['identity']==r['predicted_id']),key=lambda i:r['gallery_image_cosines'][i])
                                false_cases.append({'stage':stage,'condition':condition['name'],'rule':rule['name'],'threshold_method':method,
                                    'query_id':r['query_id'],'true_anonymous_id':r['identity'],'registered':r['is_known'],'candidate_id':r['predicted_id'],
                                    'cosine':r['similarity'],'threshold':t,'query_local_path':qrows[j]['local_path'],'gallery_local_path':grows[gi]['local_path']})
                    if fileprefix!='real_event':
                        m=metrics(rows);saved=valsummary['metrics'][method] if stage=='validation' else load(directory/('evaluation_'+method+'_summary.json'))['curated_metrics']
                        assert all(m[k]==saved[k] for k in m)
                        all_metrics.append({'stage':stage,'condition':condition['name'],'rule':rule['name'],'threshold_method':method,'threshold':t,**m})
        reg=directory/'baseline_regression.json'
        if reg.exists():
            r=load(reg);assert r['all72_previous_decisions_exact'] and max(r[k] for k in ['gallery_feature_delta','labelled_query_feature_delta','real_query_feature_delta','similarity_maxdelta'])<=1e-5
    selected=max(options);saved=next(r for r in frozen['choices'] if r['condition']==condition['name'])
    assert selected[-2]==saved['selected_rule'] and selected[-1]==saved['threshold']
assert counts=={'dot_products':70700,'identity_scores':14140,'unique_retrieval_rows':2540,'threshold_decisions':5080}
assert max(max_dot,max_identity)<1e-12 and maximum_unit_norm_error<2e-6
choice={r['condition']:r['selected_rule'] for r in frozen['choices']}
selected_errors=[r for r in false_cases if r['stage']=='evaluation' and r['threshold_method']=='validation_calibrated' and choice[r['condition']]==r['rule']]
selected_actual=[r for r in real_outcomes if r['threshold_method']=='validation_calibrated' and choice[r['condition']]==r['rule']]
save(ROOT/'results/metric_table.json',all_metrics);save(ROOT/'results/all_false_accept_cases.json',false_cases);save(ROOT/'results/selected_rule_false_accept_cases.json',selected_errors)
save(ROOT/'results/all_real_event_outcomes.json',real_outcomes);save(ROOT/'results/selected_rule_actual_outcomes.json',selected_actual)
save(ROOT/'results/independent_validation_thresholds.json',val_selection)
for name,rows in [('metrics',all_metrics),('selected_errors',selected_errors),('real_event_outcomes',real_outcomes)]:
    if rows:
        file=ROOT/'results'/(name+'.csv');assert not file.exists()
        with file.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
result={'status':'ALL5080_DECISIONS70700_DOTS20_CALIBRATIONS5_SELECTIONS_AND728_IMAGE_TRANSFORMS_INDEPENDENTLY_VERIFIED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/study_v1.json'),'frozen_selection_sha256':sha(STUDY/'selection_frozen.json'),
    'counts':counts,'validation_thresholds_verified':20,'validation_rule_selections_verified':5,'unique_rule_source_image_transforms_verified':728,
    'transform_log_rows_verified':3640,'previous510_P0_evaluation_tensor_hashes_exact':True,'validation_first_image_accesses':80,
    'all182_unique_image_accesses':182,'only_validation_available_to_current_selection':True,
    'maximum_dot_difference':max_dot,'maximum_identity_score_difference':max_identity,'maximum_embedding_unitnorm_error':maximum_unit_norm_error,
    'selected_evaluation_error_model_query_pairs':len(selected_errors),'selected_evaluation_error_distinct_query_images':len({r['query_id'] for r in selected_errors}),
    'selected_actual_candidate_pairs':sum(r['accepted'] for r in selected_actual),
    'selected_actual_candidate_events':len({r['query_id'] for r in selected_actual if r['accepted']}),
    'new_training_updates':0,'new_independent_test':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
save(ROOT/'results/independent_verification.json',result)
print(json.dumps(result))
