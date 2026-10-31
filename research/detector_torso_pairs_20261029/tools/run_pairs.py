"""Generate actual native image/detector/reference pairs; all failures retained."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import os,sys,json,hashlib,gzip,time,shutil,math,resource,socket
import cv2,numpy as np,torch,ultralytics
from ultralytics import YOLO
from geometry import reference,assign,crop_box,crop_metrics,target
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,value):assert not p.exists(),p;p.write_text(json.dumps(value,indent=2)+'\n')
def savegz(p,value):
    assert not p.exists(),p
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(value,separators=(',',':')).encode())
def stats(values):
    if not values:return None
    a=np.asarray(values,dtype=float);return {'count':len(a),'minimum':float(a.min()),'p10':float(np.quantile(a,.1)),
    'median':float(np.median(a)),'p90':float(np.quantile(a,.9)),'maximum':float(a.max()),'mean':float(a.mean())}
def aggregate(rows,condition,split):
    refs=[r for image in rows for r in image['reference_pairs']];matched=[r for r in refs if r['matched_prediction_index'] is not None]
    pred=sum(r['prediction_count'] for r in rows);matched_count=len(matched);counts={'images':len(rows),'references':len(refs),'predictions':pred,
    'matched':matched_count,'unmatched_references':len(refs)-matched_count,'unmatched_predictions':pred-matched_count,
    'reference_AABB_recall':matched_count/len(refs),'prediction_precision_vs_reference_AABB':matched_count/pred if pred else None}
    strata={}
    for name,subset in [('all',refs),('complete',[r for r in refs if r['reference_complete']]),('clipped',[r for r in refs if not r['reference_complete']])]:
        paired=[r for r in subset if r['matched_prediction_index'] is not None]
        strata[name]={'reference_count':len(subset),'matched':len(paired),'unmatched':len(subset)-len(paired),
        'engineering_crop_gate_passes':sum(r['crop_metrics']['passes_engineering_crop_gate'] for r in paired),
        'ideal_AABB_exterior_fraction_all_references':stats([r['ideal_AABB_exterior_fraction'] for r in subset]),
        'metrics_on_matched':{key:stats([r['crop_metrics'][key] for r in paired]) for key in ['reference_coverage','reference_exterior_fraction','polygon_IoU','center_error_native_px']}}
    by_date={}
    for date in sorted({r['capture_date'] for r in rows}):
        d=[r for r in rows if r['capture_date']==date];g=sum(len(r['reference_pairs']) for r in d);tp=sum(sum(a['matched_prediction_index'] is not None for a in r['reference_pairs']) for r in d)
        by_date[date]={'images':len(d),'references':g,'matched':tp,'unmatched_references':g-tp,'predictions':sum(r['prediction_count'] for r in d)}
    return {'condition':condition,'split':split,**counts,'strata':strata,'by_date':by_date}
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01' and torch.cuda.is_available()
    assert ultralytics.__version__=='8.4.63';cv2.setNumThreads(1);torch.set_num_threads(4)
    torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
    protocol=load(ROOT/'protocol/pairs_v1.json');manifest=load(ROOT/'input/images_and_references.json');preflight=load(ROOT/'results/geometry_preflight.json')
    assert sha(ROOT/'input/images_and_references.json')==protocol['new_pair_manifest_sha256']==preflight['source_manifest_sha256']
    assert sha(ROOT/'tools/geometry.py')==preflight['geometry_module_sha256']
    assert len(manifest['train'])==6809 and len(manifest['val'])==1571
    out=ROOT/'results/pairs';out.mkdir(exist_ok=False);sources=out/'case_sources';sources.mkdir()
    geometries={}
    for split,images in manifest.items():
        geometries[split]=[{**row,'references':[reference(a) for a in row['reference_annotations']]} for row in images]
    savegz(out/'source_geometry.json.gz',geometries)
    for c in protocol['models']:assert sha(Path(c['checkpoint']))==c['sha256']
    save(out/'gate_before_predictions.json',{'protocol_sha256':sha(ROOT/'protocol/pairs_v1.json'),'pair_manifest_sha256':sha(ROOT/'input/images_and_references.json'),
        'all_four_checkpoints_frozen':True,'training_reference_images':6809,'validation_reference_images':1571,
        'new_training_updates':0,'candidate_final_pixels_allowed':False})
    started=time.monotonic_ns();image_audit={};summaries=[];forwards=0;shape_counts=Counter();inference_calls=0;case_records=[];target_counts={}
    def predict_start(predictor):
        if getattr(predictor,'_torso_hooked',False):return
        original=predictor.inference
        def inference(im,*args,**kwargs):
            nonlocal inference_calls
            inference_calls+=int(im.shape[0]);shape_counts[str(tuple(im.shape))]+=1
            return original(im,*args,**kwargs)
        predictor.inference=inference;predictor._torso_hooked=True
    for condition in protocol['models']:
        model=YOLO(condition['checkpoint']);cow=[int(k) for k,v in model.names.items() if v=='cow'];assert len(cow)==1
        model.add_callback('on_predict_start',predict_start)
        splits=['train','val'] if condition['name']=='seed26' else ['val']
        for split in splits:
            prediction_rows=[];pair_rows=[];targets=[]
            for ii,row in enumerate(geometries[split]):
                file=Path(row['image_alias']);data=file.read_bytes();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
                native=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR);assert native.shape==(720,1280,3)
                rotated=np.rot90(native,k=-1).copy();rgbhash=hashlib.sha256(native[:,:,::-1].copy().tobytes()).hexdigest()
                rot_hash=hashlib.sha256(rotated[:,:,::-1].copy().tobytes()).hexdigest()
                info={'file_name':row['file_name'],'split':split,'source_sha256':row['sha256'],'native_RGB_pixel_sha256':rgbhash,
                    'clockwise90_RGB_pixel_sha256':rot_hash,'native_size_WH':[1280,720],'rotated_size_WH':[720,1280]}
                if row['file_name'] in image_audit:assert image_audit[row['file_name']]==info
                else:image_audit[row['file_name']]=info
                result=model.predict(rotated,imgsz=640,rect=True,batch=1,conf=.2,iou=.5,classes=cow,max_det=300,
                    half=False,augment=False,device=0,verbose=False)[0];forwards+=1
                assert result.orig_shape==(1280,720)
                xyxy=result.boxes.xyxy.detach().cpu().numpy().astype(float).tolist()
                confidences=result.boxes.conf.detach().cpu().numpy().astype(float).tolist();predictions=[]
                for pi,(box,conf) in enumerate(zip(xyxy,confidences)):
                    assert conf>=.2-1e-7 and np.isfinite(box).all()
                    x1,y1,x2,y2=box;native_box=[y1,720-x2,y2,720-x1]
                    native_box=[min(max(v,0.),bound) for v,bound in zip(native_box,[1280,720,1280,720])]
                    assert native_box[0]<native_box[2] and native_box[1]<native_box[3]
                    integer=crop_box(native_box)
                    predictions.append({'prediction_index':pi,'clockwise90_xyxy':box,'native_xyxy':native_box,'integer_crop_box':integer,'confidence':conf})
                matches,matrix=assign([r['visible_reference_AABB'] for r in row['references']],[r['native_xyxy'] for r in predictions])
                pair_by_ref={a:(b,iou) for a,b,iou in matches};matched_pred={b for a,b,iou in matches};pairs=[]
                for ri,ref in enumerate(row['references']):
                    pair={'reference_index':ri,'annotation_key':ref['annotation_key'],'reference_complete':ref['reference_complete'],
                        'visible_reference_fraction':ref['visible_reference_fraction'],'visible_reference_area':ref['visible_reference_area'],
                        'ideal_AABB_exterior_fraction':ref['ideal_AABB_exterior_fraction'],'matched_prediction_index':None,
                        'best_any_prediction_AABB_IoU':float(matrix[ri].max()) if len(predictions) else None}
                    if ri in pair_by_ref:
                        pi,iou=pair_by_ref[ri];pred=predictions[pi];box=pred['integer_crop_box'];m=crop_metrics(ref,box)
                        pair.update({'matched_prediction_index':pi,'matched_reference_AABB_IoU':iou,'crop_box':box,'crop_metrics':m,
                            'localizer_target_native_crop_cx_cy_long_short_sin2_cos2':target(ref,box)})
                        targets.append({'annotation_key':ref['annotation_key'],'file_name':row['file_name'],'capture_date':row['capture_date'],
                            'source_path':row['image_alias'],'source_sha256':row['sha256'],'crop_box':box,'reference_complete':ref['reference_complete'],
                            'visible_reference_fraction':ref['visible_reference_fraction'],'target':pair['localizer_target_native_crop_cx_cy_long_short_sin2_cos2'],
                            'crop_metrics':m,'target_is_animal_identity':False,'headtail_direction_known':False})
                    pairs.append(pair)
                prediction_rows.append({'file_name':row['file_name'],'split':split,'source_sha256':row['sha256'],'capture_date':row['capture_date'],
                    'predictions':predictions})
                pair_rows.append({'file_name':row['file_name'],'capture_date':row['capture_date'],'prediction_count':len(predictions),
                    'reference_pairs':pairs,'unmatched_prediction_indices':[i for i in range(len(predictions)) if i not in matched_pred]})
                if ii%256==0:print(json.dumps({'condition':condition['name'],'split':split,'images_completed':ii+1,'image_forwards':forwards}),flush=True)
            stem=split+'_'+condition['name']
            savegz(out/(stem+'_predictions.json.gz'),prediction_rows);savegz(out/(stem+'_reference_pairs.json.gz'),pair_rows);savegz(out/(stem+'_crop_targets.json.gz'),targets)
            aggregate_result=aggregate(pair_rows,condition['name'],split);save(out/(stem+'_summary.json'),aggregate_result);summaries.append(aggregate_result)
            target_counts[stem]=len(targets)
            if split=='val':
                by_image={r['file_name']:r for r in geometries[split]};pred_by_image={r['file_name']:r for r in prediction_rows}
                allrefs=[{**r,'file_name':im['file_name']} for im in pair_rows for r in im['reference_pairs']]
                matched=[r for r in allrefs if r['matched_prediction_index'] is not None];missing=[r for r in allrefs if r['matched_prediction_index'] is None]
                chosen=[]
                if condition['name']=='seed26':
                    for name in protocol['fixed_validation_sample_names']:
                        ref=max(by_image[name]['references'],key=lambda r:r['visible_reference_area'])
                        pair=next(r for r in allrefs if r['file_name']==name and r['annotation_key']==ref['annotation_key'])
                        chosen.append(('preset_hash_ranked_validation',pair))
                if matched:
                    chosen.extend([('minimum_matched_reference_coverage',min(matched,key=lambda r:(r['crop_metrics']['reference_coverage'],r['annotation_key']))),
                    ('maximum_matched_reference_exterior_fraction',max(matched,key=lambda r:(r['crop_metrics']['reference_exterior_fraction'],r['annotation_key'])))])
                complete=[r for r in allrefs if r['reference_complete']]
                if complete:chosen.append(('maximum_complete_reference_envelope_exterior_fraction',max(complete,key=lambda r:(r['ideal_AABB_exterior_fraction'],r['annotation_key']))))
                if missing:chosen.append(('maximum_visible_reference_area_among_unmatched',max(missing,key=lambda r:(r['visible_reference_area'],r['annotation_key']))))
                for criterion,pair in chosen:
                    row=by_image[pair['file_name']];file=Path(row['image_alias']);dest=sources/row['file_name']
                    if not dest.exists():shutil.copyfile(file,dest)
                    assert sha(dest)==row['sha256']
                    case_records.append({'condition':condition['name'],'criterion':criterion,
                        'selection_is_postprediction_diagnostic':not criterion.startswith('preset'),
                        'source_file_relative':dest.relative_to(ROOT).as_posix(),'source_sha256':row['sha256'],'source_pixel_audit':image_audit[row['file_name']],
                        'source_date':row['capture_date'],'source_image_size_WH':[1280,720],'pair':pair,
                        'reference':next(r for r in row['references'] if r['annotation_key']==pair['annotation_key']),
                        'all_native_predictions':pred_by_image[row['file_name']]['predictions']})
            print(json.dumps({'condition_split_completed':stem,'matched':aggregate_result['matched'],'missed':aggregate_result['unmatched_references'],
                'extra_predictions':aggregate_result['unmatched_predictions'],'pair_targets':len(targets),'image_forwards':forwards}),flush=True)
        assert sha(Path(condition['checkpoint']))==condition['sha256']
        del model;torch.cuda.empty_cache()
    assert forwards==inference_calls==13093 and len(image_audit)==8380
    assert shape_counts==Counter({'(1, 3, 640, 384)':13093}),shape_counts
    save(out/'image_audit.json',list(image_audit.values()));save(out/'case_selection.json',case_records)
    result={'status':'ACTUAL640_DETECTOR_TORSO_SOURCE_PAIRS_ALL8380_IMAGES_AND4_VALIDATION_MODELS_COMPLETE',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'node':socket.gethostname(),
        'protocol_sha256':sha(ROOT/'protocol/pairs_v1.json'),'pair_manifest_sha256':sha(ROOT/'input/images_and_references.json'),
        'torch':torch.__version__,'ultralytics':ultralytics.__version__,'opencv':cv2.__version__,
        'detector_actual_image_forwards':forwards,'active_predictor_inference_image_calls':inference_calls,
        'predictor_input_tensor_shape_counts':dict(shape_counts),'framework_warmup_forward_not_counted_as_source_image':True,
        'unique_source_images_hashed_and_decoded':8380,'train_pair_model':'seed26','all_four_validation_models_reported':True,
        'condition_summaries':summaries,'crop_target_counts':target_counts,'case_records':len(case_records),
        'case_unique_source_files':len(list(sources.iterdir())),'new_training_updates':0,'identity_encoder_forwards':0,
        'animal_identity_labels_generated':False,'native_passage_counts_or_identity_accuracy_computed':False,
        'candidate_final_images_accessed':False,'current_counting_pipeline_changed':False,'FPGA_execution_verified':False,'whole_goal_complete':False,
        'wall_s':(time.monotonic_ns()-started)/1e9,'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'CUDA_peak_allocated_bytes':torch.cuda.max_memory_allocated()}
    save(out/'summary.json',result)
    artifact=[{'relative_file':file.relative_to(ROOT).as_posix(),'bytes':file.stat().st_size,'sha256':sha(file)} for file in sorted(out.rglob('*')) if file.is_file()]
    save(ROOT/'results/artifact_manifest.json',artifact)
    print(json.dumps({k:v for k,v in result.items() if k!='condition_summaries'}),flush=True)
if __name__=='__main__':main()
