"""Independent audit of source geometry, assignment optimum, crop metrics and targets."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import hashlib,json,gzip,math,csv
import numpy as np
from PIL import Image
from independent_geometry import corners,intersection,envelope,polygon_area,iou,independent_best_matching,quad_roundtrip_error
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'delivery/results/pairs'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def numeric_stats(values):
    if not values:return None
    a=np.asarray(values,dtype=float)
    return {'count':len(a),'minimum':float(min(a)),'p10':float(np.quantile(a,.1)),'median':float(np.quantile(a,.5)),
            'p90':float(np.quantile(a,.9)),'maximum':float(max(a)),'mean':float(sum(a)/len(a))}
protocol=load(ROOT/'protocol/pairs_v1.json');summary=load(OUT/'summary.json');manifest=load(ROOT/'input/images_and_references.json')
geometry=loadgz(OUT/'source_geometry.json.gz');assert summary['protocol_sha256']==sha(ROOT/'protocol/pairs_v1.json')
assert summary['detector_actual_image_forwards']==summary['active_predictor_inference_image_calls']==13093
assert summary['predictor_input_tensor_shape_counts']=={'(1, 3, 640, 384)':13093}
reference_index={};image_index={};maxarea=maxcoord=0.;refcounts=Counter();ref_poly={}
for split,images in geometry.items():
    assert len(images)==len(manifest[split])
    for image,src in zip(images,manifest[split]):
        assert image['file_name']==src['file_name'] and image['sha256']==src['sha256']
        image_index[(split,image['file_name'])]=image
        for ref,ann in zip(image['references'],src['reference_annotations']):
            assert ref['annotation_key']==ann['annotation_key'] and ref['bbox_xywh_angle_rad']==ann['bbox_xywh_angle_rad']
            key=ref['annotation_key'];assert key not in reference_index
            full=corners(ann['bbox_xywh_angle_rad']);visible=intersection(full,[0,0,1280,720]);varea=polygon_area(visible);box=envelope(visible)
            maxarea=max(maxarea,abs(varea-ref['visible_reference_area']));maxcoord=max(maxcoord,max(abs(a-b) for a,b in zip(box,ref['visible_reference_AABB'])))
            assert abs(varea-ref['visible_reference_area'])<1e-6 and max(abs(a-b) for a,b in zip(box,ref['visible_reference_AABB']))<1e-8
            xa,ya,w,h,angle=ann['bbox_xywh_angle_rad'];area=w*h;complete=varea/area>=1-1e-8
            assert complete==ref['reference_complete'] and abs(ref['visible_reference_fraction']-varea/area)<1e-10
            ideal=1-varea/((box[2]-box[0])*(box[3]-box[1]));assert abs(ideal-ref['ideal_AABB_exterior_fraction'])<1e-10
            reference_index[key]=ref;ref_poly[key]=visible;refcounts[split+'_references']+=1;refcounts[split+'_complete' if complete else split+'_clipped']+=1
assert len(reference_index)==10752
audit=load(OUT/'image_audit.json');assert len(audit)==8380
max_crop_delta=max_target_roundtrip=max_native_box_delta=0.;pair_count=target_count=prediction_count=matrix_pairs=ambiguous_match_images=0
metric_rows=[];all_condition_crop_rows=[];condition_pairs={}
for saved in summary['condition_summaries']:
    split=saved['split'];condition=saved['condition'];stem=split+'_'+condition
    predictions=loadgz(OUT/(stem+'_predictions.json.gz'));pairs=loadgz(OUT/(stem+'_reference_pairs.json.gz'));targets=loadgz(OUT/(stem+'_crop_targets.json.gz'))
    assert len(predictions)==len(pairs)==len(geometry[split]);by_target={r['annotation_key']:r for r in targets};assert len(by_target)==len(targets)
    c=Counter();metric_values=defaultdict(lambda:defaultdict(list));ideal_values=defaultdict(list);day_counts=defaultdict(Counter);flat=[]
    for im,pred,image in zip(pairs,predictions,geometry[split]):
        assert im['file_name']==pred['file_name']==image['file_name'];refs=image['references'];ps=pred['predictions'];assert len(refs)==len(im['reference_pairs'])
        assert len(ps)==im['prediction_count'];matrix=[]
        for pr in ps:
            x1,y1,x2,y2=pr['clockwise90_xyxy'];box=[y1,720-x2,y2,720-x1]
            max_native_box_delta=max(max_native_box_delta,max(abs(a-b) for a,b in zip(box,pr['native_xyxy'])))
            assert max(abs(a-b) for a,b in zip(box,pr['native_xyxy']))<1e-6 and .2-1e-7<=pr['confidence']<=1.
            crop=[max(0,math.floor(box[0])),max(0,math.floor(box[1])),min(1280,math.ceil(box[2])),min(720,math.ceil(box[3]))]
            assert crop==pr['integer_crop_box'];prediction_count+=1
        for ref in refs:matrix.append([iou(ref['visible_reference_AABB'],pr['native_xyxy']) for pr in ps])
        matrix_pairs+=len(refs)*len(ps);best,num=independent_best_matching(matrix)
        if num>1:ambiguous_match_images+=1
        found=[r for r in im['reference_pairs'] if r['matched_prediction_index'] is not None]
        assigned=[r['matched_prediction_index'] for r in found];assert len(assigned)==len(set(assigned))
        assert len(found)==best[0] and abs(sum(r['matched_reference_AABB_IoU'] for r in found)-best[1])<1e-10
        assert set(im['unmatched_prediction_indices'])==set(range(len(ps)))-set(assigned)
        assert sorted(r['reference_index'] for r in im['reference_pairs'])==list(range(len(refs)))
        c.update({'images':1,'references':len(refs),'predictions':len(ps),'matched':len(found),'unmatched_references':len(refs)-len(found),'unmatched_predictions':len(ps)-len(found)})
        day_counts[image['capture_date']].update({'images':1,'references':len(refs),'predictions':len(ps),'matched':len(found),'unmatched_references':len(refs)-len(found)})
        for ref,r in zip(refs,im['reference_pairs']):
            pair_count+=1;assert r['annotation_key']==ref['annotation_key'];stratum='complete' if ref['reference_complete'] else 'clipped'
            expected_best=max(matrix[r['reference_index']]) if ps else None
            assert r['best_any_prediction_AABB_IoU']==expected_best or expected_best is not None and abs(r['best_any_prediction_AABB_IoU']-expected_best)<1e-12
            for st in ['all',stratum]:ideal_values[st].append(ref['ideal_AABB_exterior_fraction'])
            if r['matched_prediction_index'] is None:assert r['annotation_key'] not in by_target;continue
            pr=ps[r['matched_prediction_index']];box=pr['integer_crop_box'];assert r['crop_box']==box
            intersect=polygon_area(intersection(ref_poly[ref['annotation_key']],box));ca=(box[2]-box[0])*(box[3]-box[1]);ra=ref['visible_reference_area']
            coverage=min(1.,max(0.,intersect/ra));outside=1-min(1.,max(0.,intersect/ca));poly_iou=intersect/(ca+ra-intersect)
            rb=ref['visible_reference_AABB'];center_error=math.hypot((rb[0]+rb[2]-box[0]-box[2])/2,(rb[1]+rb[3]-box[1]-box[3])/2)
            expected={'intersection_reference_crop_area':intersect,'reference_coverage':coverage,'reference_exterior_fraction':outside,'polygon_IoU':poly_iou,'center_error_native_px':center_error}
            for key,value in expected.items():
                delta=abs(value-r['crop_metrics'][key]);max_crop_delta=max(max_crop_delta,delta)
                assert delta<(1e-6 if key=='intersection_reference_crop_area' else 1e-8)
            assert r['crop_metrics']['passes_engineering_crop_gate']==(coverage>=.9 and outside<=.25)
            target_row=by_target[ref['annotation_key']];t=target_row['target'];assert t==r['localizer_target_native_crop_cx_cy_long_short_sin2_cos2'] and target_row['crop_box']==box
            assert target_row['target_is_animal_identity'] is False and target_row['headtail_direction_known'] is False
            err=quad_roundtrip_error(ref['full_native_quad'],t,box);max_target_roundtrip=max(max_target_roundtrip,err);assert err<1e-7
            assert abs(t[4]**2+t[5]**2-1)<1e-10;target_count+=1
            for st in ['all',stratum]:
                for key,value in [('reference_coverage',coverage),('reference_exterior_fraction',outside),('polygon_IoU',poly_iou),('center_error_native_px',center_error),('gate',int(coverage>=.9 and outside<=.25))]:
                    metric_values[st][key].append(value)
            all_condition_crop_rows.append({'split':split,'condition':condition,'file_name':image['file_name'],'annotation_key':ref['annotation_key'],'reference_complete':ref['reference_complete'],
                'reference_coverage':coverage,'reference_exterior_fraction':outside,'polygon_IoU':poly_iou,
                'ideal_AABB_exterior_fraction':ref['ideal_AABB_exterior_fraction'],'passes_engineering_crop_gate':coverage>=.9 and outside<=.25})
        flat.extend({**r,'file_name':image['file_name']} for r in im['reference_pairs'])
    assert c['matched']==len(targets)
    assert all(c[k]==saved[k] for k in c)
    assert all(dict(v)==saved['by_date'][day] for day,v in day_counts.items())
    for st in ['all','complete','clipped']:
        actual=saved['strata'][st];assert actual['reference_count']==len(ideal_values[st]) and actual['matched']==len(metric_values[st]['reference_coverage'])
        assert actual['engineering_crop_gate_passes']==sum(metric_values[st]['gate'])
        for name in ['reference_coverage','reference_exterior_fraction','polygon_IoU','center_error_native_px']:
            recalculated=numeric_stats(metric_values[st][name]);record=actual['metrics_on_matched'][name]
            for key,value in recalculated.items():assert abs(value-record[key])<1e-7
        recalculated=numeric_stats(ideal_values[st]);record=actual['ideal_AABB_exterior_fraction_all_references']
        for key,value in recalculated.items():assert abs(value-record[key])<1e-9
        metric_rows.append({'condition':condition,'split':split,'stratum':st,'references':actual['reference_count'],'matched':actual['matched'],
            'gate_passes':actual['engineering_crop_gate_passes'],'coverage_median':actual['metrics_on_matched']['reference_coverage']['median'],
            'outside_median':actual['metrics_on_matched']['reference_exterior_fraction']['median'],
            'ideal_outside_median':actual['ideal_AABB_exterior_fraction_all_references']['median']})
    condition_pairs[(split,condition)]=flat
cases=load(OUT/'case_selection.json');case_rule_verifications=0;source_files=set();decode_checks=[]
for case in cases:
    rows=condition_pairs[('val',case['condition'])];criterion=case['criterion'];chosen=case['pair'];key=chosen['annotation_key']
    if criterion=='preset_hash_ranked_validation':
        assert case['selection_is_postprediction_diagnostic'] is False
        assert Path(case['source_file_relative']).name in protocol['fixed_validation_sample_names']
        image=image_index[('val',Path(case['source_file_relative']).name)];expected=max(image['references'],key=lambda r:r['visible_reference_area'])['annotation_key']
    elif criterion=='minimum_matched_reference_coverage':expected=min((r for r in rows if r['matched_prediction_index'] is not None),key=lambda r:(r['crop_metrics']['reference_coverage'],r['annotation_key']))['annotation_key']
    elif criterion=='maximum_matched_reference_exterior_fraction':expected=max((r for r in rows if r['matched_prediction_index'] is not None),key=lambda r:(r['crop_metrics']['reference_exterior_fraction'],r['annotation_key']))['annotation_key']
    elif criterion=='maximum_complete_reference_envelope_exterior_fraction':expected=max((r for r in rows if r['reference_complete']),key=lambda r:(r['ideal_AABB_exterior_fraction'],r['annotation_key']))['annotation_key']
    elif criterion=='maximum_visible_reference_area_among_unmatched':expected=max((r for r in rows if r['matched_prediction_index'] is None),key=lambda r:(r['visible_reference_area'],r['annotation_key']))['annotation_key']
    else:raise AssertionError(criterion)
    assert expected==key;case_rule_verifications+=1
    file=ROOT/'delivery'/case['source_file_relative'];assert sha(file)==case['source_sha256']
    if file not in source_files:
        with Image.open(file) as im:im.load();image=im.convert('RGB');assert image.size==(1280,720);pixel=hashlib.sha256(image.tobytes()).hexdigest()
        assert pixel==case['source_pixel_audit']['native_RGB_pixel_sha256'];source_files.add(file);decode_checks.append({'path':str(file.resolve()),'sha256':sha(file),'RGB_pixel_sha256':pixel})
assert pair_count==8888+4*1864 and sum(len(loadgz(OUT/(r['split']+'_'+r['condition']+'_crop_targets.json.gz'))) for r in summary['condition_summaries'])==target_count
save(ROOT/'results/independent_metric_table.json',metric_rows);save(ROOT/'results/independent_crop_rows.json',all_condition_crop_rows);save(ROOT/'results/case_source_pixel_verification.json',decode_checks)
with (ROOT/'results/metrics.csv').open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(metric_rows[0]));w.writeheader();w.writerows(metric_rows)
result={'status':'ALL_SOURCE_ROTATED_GEOMETRY_ASSIGNMENTS_ACTUAL_CROP_METRICS_AND_LOCALIZER_TARGETS_INDEPENDENTLY_VERIFIED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'unique_references':10752,'reference_condition_rows':pair_count,'matched_crop_targets':target_count,
    'predicted_boxes_native_inverse_verified':prediction_count,'assignment_candidate_IoUs':matrix_pairs,'one_to_one_image_assignments_verified':13093,
    'multiple_optimal_assignment_image_cases':ambiguous_match_images,'maximum_reference_area_difference':maxarea,'maximum_reference_AABB_corner_difference':maxcoord,
    'maximum_crop_metric_difference_including_native_area':max_crop_delta,'maximum_target_quad_roundtrip_native_px':max_target_roundtrip,
    'maximum_inverse_box_coordinate_difference':max_native_box_delta,'case_selection_rules_verified':case_rule_verifications,
    'downloaded_native_case_images_pixel_verified':len(source_files),'all_incomplete_and_unmatched_references_preserved':True,
    'new_training_updates':0,'animal_identity_labels_generated':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
save(ROOT/'results/independent_verification.json',result);print(json.dumps(result))
