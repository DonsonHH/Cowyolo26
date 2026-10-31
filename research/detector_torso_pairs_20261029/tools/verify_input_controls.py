from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gzip,json,hashlib,csv
import numpy as np
from independent_geometry import iou,independent_best_matching
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/pairs';PROBE=ROOT/'delivery/results/input_controls'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n')
p=load(ROOT/'protocol/input_controls_v1.json');rows=load(PROBE/'rows.json');s=load(PROBE/'summary.json');tensors=load(PROBE/'tensor_records.json')
geometry={r['file_name']:r for r in loadgz(OUT/'source_geometry.json.gz')['val']};main=load(OUT/'summary.json')
assert s['protocol_sha256']==sha(ROOT/'protocol/input_controls_v1.json') and len(rows)==len(tensors)==288
counts=Counter();maxdelta=0.;baseline_repeats=0;old320_cases=0;old320_all=True
ref_boxes_by_name={name:[r['visible_reference_AABB'] for r in image['references']] for name,image in geometry.items()}
for row,tensor in zip(rows,tensors):
    assert row['condition']==tensor['condition'] and row['config_index']==tensor['config_index'] and row['file_name']==tensor['file_name']
    expected=p['configurations'][row['config_index']];assert row['config']==expected
    native=[r['native_xyxy'] for r in row['predictions']]
    matrix=[[iou(gt,pred) for pred in native] for gt in ref_boxes_by_name[row['file_name']]]
    optimum,num=independent_best_matching(matrix);assert optimum[0]==row['matched']
    assert row['unmatched_references']==len(matrix)-row['matched'] and row['unmatched_predictions']==len(native)-row['matched']
    currentgt=[[720-b[3],b[0],720-b[1],b[2]] for b in ref_boxes_by_name[row['file_name']]] if expected['orientation']=='clockwise90' else ref_boxes_by_name[row['file_name']]
    for gi,g in enumerate(currentgt):
        for pi,pred in enumerate(row['predictions']):
            value=iou(g,pred['current_xyxy']);delta=abs(matrix[gi][pi]-value);maxdelta=max(maxdelta,delta);assert delta<1e-10
    if expected['rect']:
        shape=[1,3,640,384] if expected['imgsz']==640 and expected['orientation']=='clockwise90' else (
              [1,3,384,640] if expected['imgsz']==640 else ([1,3,320,192] if expected['orientation']=='clockwise90' else [1,3,192,320]))
    else:shape=[1,3,expected['imgsz'],expected['imgsz']]
    assert tensor['tensor_shape']==shape
    if row['config_index'] in [0,8]:baseline_repeats+=1
    if 'prior320_square_regression' in row:
        old320_cases+=1;old320_all=old320_all and row['prior320_square_regression']['all_boxes_correspond']
    counts[(row['condition'],row['config_index'],'matched')]+=row['matched']
    counts[(row['condition'],row['config_index'],'references')]+=row['references']
for metric in s['metrics']:
    assert metric['matched']==counts[(metric['condition'],metric['config_index'],'matched')] and metric['references']==counts[(metric['condition'],metric['config_index'],'references')]
for config in range(9):
    for filename in p['sample_names']:
        hashes={r['tensor_sha256'] for r in tensors if r['config_index']==config and r['file_name']==filename}
        assert len(hashes)==1
for condition in p['models']:
    for filename in p['sample_names']:
        first=next(r for r in tensors if r['condition']==condition['name'] and r['file_name']==filename and r['config_index']==0)
        last=next(r for r in tensors if r['condition']==condition['name'] and r['file_name']==filename and r['config_index']==8)
        assert first['tensor_sha256']==last['tensor_sha256']
assert baseline_repeats==64 and old320_cases==48 and old320_all
baselines=[];source_records=[]
for condition in p['models']:
    if condition['seed'] is None:continue
    for orientation in ['original','clockwise90']:
        file=PROJECT/'orientation_validation_20261027/delivery/results/control'/('seed'+str(condition['seed'])+'_'+orientation+'_predictions.json.gz')
        old=loadgz(file);assert len(old)==1571;total=Counter()
        for row in old:
            image=geometry[row['file_name']];assert image['sha256']==row['source_SHA256']
            predicted=[r['xyxy'] for r in row['predictions'] if r['confidence']>=.2]
            if orientation=='clockwise90':native=[[b[1],720-b[2],b[3],720-b[0]] for b in predicted]
            else:native=predicted
            matrix=[[iou(gt,pr) for pr in native] for gt in ref_boxes_by_name[row['file_name']]]
            optimum,_=independent_best_matching(matrix);tp=optimum[0]
            total.update({'images':1,'references':len(matrix),'predictions':len(native),'matched':tp,
                'unmatched_references':len(matrix)-tp,'unmatched_predictions':len(native)-tp})
        baselines.append({'condition':condition['name'],'source_kind':'previous_frozen_cache','orientation':orientation,'imgsz':320,
                         'rect':False,'batch':16,'inference_confidence_floor':.01,'evaluated_confidence_threshold':.2,**dict(total)})
        source_records.append({'path':str(file.resolve()),'sha256':sha(file)})
    current=next(r for r in main['condition_summaries'] if r['condition']==condition['name'] and r['split']=='val')
    baselines.append({'condition':condition['name'],'source_kind':'new_actual_predictions','orientation':'clockwise90','imgsz':640,'rect':True,'batch':1,
        'inference_confidence_floor':.2,'evaluated_confidence_threshold':.2,**{k:current[k] for k in ['images','references','predictions','matched','unmatched_references','unmatched_predictions']}})
ideal_complete=[r['ideal_AABB_exterior_fraction'] for im in geometry.values() for r in im['references'] if r['reference_complete']]
assert len(ideal_complete)==919
result={'status':'INPUT288_CASES_IOU_INVARIANCE64_BASELINE_REPEATS48_PRIOR320_CORRESPONDENCES_AND6_FULL_CACHE_REPLAYS_VERIFIED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'probe_source_forwards':288,'pair_baseline_repeat_cases':64,
    'prior320_square_sample_correspondence_cases':48,'prior320_sample_all_boxes_correspond_at_IoU0999':old320_all,
    'maximum_rotation_inverse_IoU_difference':maxdelta,'same_source_preprocess_tensor_hashes_identical_across_all4models':True,
    'first_last_main_tensor_hashes_equal':True,'cached_full_validation_replays':6,'cached_image_retrievals_not_new_model_forwards':1571*6,
    'complete_reference_boxes':919,'ideal_AABB_exterior_above025':sum(v>.25 for v in ideal_complete),
    'protocol_sha256':sha(ROOT/'protocol/input_controls_v1.json'),'no_full_set_320vs640_single_factor_claim':True,
    'scope':'Fullcachecomparisonsdifferinrect/batch/floor;onlyfixed8factorialiscontrolledcontrast.Samealreadyuseddevelopmentdates.',
    'whole_goal_complete':False}
save(ROOT/'results/input_controls_verification.json',result);save(ROOT/'results/full_cache_vs_current640.json',{'rows':baselines,'sources':source_records})
with (ROOT/'results/input_factorial.csv').open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(s['metrics'][0]));w.writeheader();w.writerows(s['metrics'])
with (ROOT/'results/cache_vs_640.csv').open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(baselines[0]));w.writeheader();w.writerows(baselines)
print(json.dumps(result))
for r in baselines:print(r['condition'],r['source_kind'],r['orientation'],r['imgsz'],'matched',r['matched'],'missed',r['unmatched_references'],'extra',r['unmatched_predictions'])
