"""Paired all-validation image prediction with frozen weights, no training."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import concurrent.futures,hashlib,json,os,socket,time,gzip,struct
import numpy as np,cv2,torch,ultralytics
from scipy.optimize import linear_sum_assignment
from ultralytics import YOLO
from ultralytics.data.augment import LetterBox

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda:f.read(4*1024*1024),b''):h.update(part)
    return h.hexdigest()


def save(path,value):
    assert not path.exists();path.write_text(json.dumps(value,indent=2),encoding='utf-8')


def iou_matrix(a,b):
    a=np.asarray(a,dtype=np.float64).reshape(-1,4);b=np.asarray(b,dtype=np.float64).reshape(-1,4)
    lo=np.maximum(a[:,None,:2],b[None,:,:2]);hi=np.minimum(a[:,None,2:],b[None,:,2:])
    intersection=np.maximum(hi-lo,0).prod(axis=2)
    area_a=(a[:,2]-a[:,0])*(a[:,3]-a[:,1]);area_b=(b[:,2]-b[:,0])*(b[:,3]-b[:,1])
    return intersection/np.maximum(area_a[:,None]+area_b[None,:]-intersection,1e-30)


def match(gt,pred,threshold):
    n,m=len(gt),len(pred)
    if not n or not m:return []
    matrix=iou_matrix(gt,pred);size=n+m;bonus=size+1.
    rewards=np.zeros((size,size));rewards[:n,:m]=np.where(matrix>=threshold,bonus+matrix,-bonus*100)
    rows,columns=linear_sum_assignment(-rewards)
    return [{'gt_index':int(a),'prediction_index':int(b),'IoU':float(matrix[a,b])}
            for a,b in zip(rows,columns) if a<n and b<m and matrix[a,b]>=threshold]


def native_gt(row):
    values=np.asarray(row['expected_float32_rows'],dtype=np.float64)
    assert (values[:,0]==0).all()
    centres=values[:,1:3]*np.asarray([1280,720]);sizes=values[:,3:5]*np.asarray([1280,720])
    return np.concatenate([centres-sizes/2,centres+sizes/2],axis=1)


def rotate_boxes(boxes,height):
    a=np.asarray(boxes,dtype=np.float64).reshape(-1,4)
    return np.stack([height-a[:,3],a[:,0],height-a[:,1],a[:,2]],axis=1)


def compute_metrics(rows,confidence,threshold):
    totals=Counter();by_date=defaultdict(Counter);pairs=[]
    for row in rows:
        predictions=[r for r in row['predictions'] if r['confidence']>=confidence]
        matches=match(row['GT_xyxy'],[r['xyxy'] for r in predictions],threshold)
        gt=len(row['GT_xyxy']);pred=len(predictions);tp=len(matches)
        values={'GT':gt,'predictions':pred,'TP':tp,'FP':pred-tp,'FN':gt-tp}
        totals.update(values);by_date[row['capture_date']].update(values)
        pairs.append({'file_name':row['file_name'],'capture_date':row['capture_date'],**values,'matches':matches})
    result={**dict(totals),'recall':totals['TP']/totals['GT'],
            'precision':totals['TP']/totals['predictions'] if totals['predictions'] else None,
            'confidence_threshold':confidence,'IoU_threshold':threshold,
            'by_date':{k:dict(v) for k,v in sorted(by_date.items())},'image_matches':pairs}
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    assert torch.cuda.is_available() and ultralytics.__version__=='8.4.63'
    cv2.setNumThreads(1);torch.set_num_threads(2)
    ppath=ROOT/'protocol/orientation_v1.json';p=json.loads(ppath.read_text())
    for entry in json.loads((ROOT/'input/staging_manifest.json').read_text()):
        path=ROOT/entry['path'];assert path.is_file() and path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256']
    freeze_path=ROOT/'input/source_checkpoint_freeze.json'
    assert sha(freeze_path)==p['source_checkpoint_freeze_sha256']
    assert sha(ROOT/'input/source_prepared_manifest.json')==p['source_prepared_manifest_sha256']
    selected=json.loads((ROOT/'input/selected_validation.json').read_text())
    assert len(selected)==1571 and sum(len(r['expected_float32_rows']) for r in selected)==1864
    assert {r['actual_split'] for r in selected}=={'val'}
    out=ROOT/'results/control';out.mkdir(exist_ok=False);visual=out/'sample_overlays';visual.mkdir()
    source_root=ROOT.parent/'cows2021_adaptation_20261027'
    for row in selected:
        assert Path(row['image_alias']).resolve().is_relative_to(source_root/'raw_images/validation')
    # Pixel and geometry checks precede any model prediction.
    toy=np.arange(3*5,dtype=np.uint8).reshape(3,5)
    assert np.array_equal(np.rot90(np.rot90(toy,k=-1),k=1),toy)
    box=np.array([[1.,0.,4.,2.]])
    assert np.array_equal(rotate_boxes(box,3),[[1.,1.,3.,4.]])
    save(out/'gate_before_predictions.json',{'protocol_sha256':sha(ppath),
         'checkpoint_freeze_sha256':sha(freeze_path),'validation_images':1571,'objects':1864,
         'integer_90degree_pixel_permutation_control':True,'box_edges_control':True,
         'training_updates':0,'source_video_or_Toros_used':False,'candidate_final_pixels_used':False})
    timer=time.perf_counter();results=[];input_records=None
    batch_size=p['prediction']['batch'];sample_names=set(p['sample_visuals']['files'])
    transform=LetterBox(new_shape=(320,320),auto=False,stride=32)
    for condition in p['checkpoints']:
        weight=Path(condition['path']);assert sha(weight)==condition['sha256']
        model=YOLO(str(weight));assert model.names=={0:'cow'}
        seed_results={name:[] for name in p['orientations']};input_audit=[]
        for start in range(0,len(selected),batch_size):
            subset=selected[start:start+batch_size];original=[];rotated=[]
            for row in subset:
                path=Path(row['image_alias']);data=path.read_bytes()
                assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
                im=cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR);assert im.shape==(720,1280,3)
                rotated_im=np.rot90(im,k=-1).copy();assert rotated_im.shape==(1280,720,3)
                assert np.array_equal(np.rot90(rotated_im,k=1),im)
                before=transform(image=im);after=transform(image=rotated_im)
                delta=np.abs(np.rot90(before,k=-1).astype(np.int16)-after.astype(np.int16))
                input_audit.append({'file_name':row['file_name'],'capture_date':row['capture_date'],
                                    'source_sha256':row['sha256'],'original_dimensions':[1280,720],
                                    'clockwise90_dimensions':[720,1280],
                                    'exact_inverse_pixel_permutation_verified':True,
                                    'letterbox_rotated_max_uint8_difference':int(delta.max()),
                                    'letterbox_rotated_different_components':int(np.count_nonzero(delta))})
                original.append(im);rotated.append(rotated_im)
            for orientation,images in [('original',original),('clockwise90',rotated)]:
                predictions=model.predict(images,imgsz=320,rect=False,batch=batch_size,conf=.01,iou=.5,
                                          classes=[0],max_det=300,half=False,augment=False,device=0,verbose=False)
                assert len(predictions)==len(subset)
                for row,im,result in zip(subset,images,predictions):
                    assert result.orig_shape==im.shape[:2]
                    boxes=result.boxes.xyxy.cpu().numpy().astype(float) if result.boxes is not None else np.empty((0,4))
                    confs=result.boxes.conf.cpu().numpy().astype(float) if result.boxes is not None else []
                    assert np.isfinite(boxes).all() and all(np.isfinite(c) for c in confs)
                    gt=native_gt(row)
                    if orientation=='clockwise90':gt=rotate_boxes(gt,720)
                    values=[{'xyxy':list(map(float,xyxy)),'confidence':float(c)} for xyxy,c in zip(boxes,confs)]
                    record={'file_name':row['file_name'],'capture_date':row['capture_date'],
                            'source_SHA256':row['sha256'],'orientation':orientation,
                            'image_dimensions_WH':[im.shape[1],im.shape[0]],
                            'GT_annotation_IDs':row['published_annotation_IDs'],'GT_xyxy':gt.tolist(),
                            'predictions':values}
                    seed_results[orientation].append(record)
                    if row['file_name'] in sample_names:
                        view=im.copy()
                        for x1,y1,x2,y2 in gt:
                            cv2.rectangle(view,(round(x1),round(y1)),(round(x2),round(y2)),(255,210,70),3)
                        for item in values:
                            if item['confidence']<.2:continue
                            x1,y1,x2,y2=item['xyxy']
                            cv2.rectangle(view,(round(x1),round(y1)),(round(x2),round(y2)),(80,235,120),3)
                            cv2.putText(view,f"{item['confidence']:.2f}",(round(x1),max(18,round(y1)-5)),cv2.FONT_HERSHEY_SIMPLEX,.7,(80,235,120),2)
                        target=visual/f"seed{condition['seed']}_{orientation}_{Path(row['file_name']).stem}.jpg"
                        assert cv2.imwrite(str(target),view)
            if start%320==0:
                print(json.dumps({'seed':condition['seed'],'images_per_orientation_predicted':min(start+batch_size,len(selected)),
                                  'validation_images':1571,'elapsed_s':time.perf_counter()-timer}),flush=True)
        if input_records is None:
            input_records=input_audit;save(out/'input_pixel_controls.json',input_records)
        else:assert input_records==input_audit
        for orientation,rows in seed_results.items():
            assert len(rows)==1571 and [r['file_name'] for r in rows]==[r['file_name'] for r in selected]
            prediction_path=out/f"seed{condition['seed']}_{orientation}_predictions.json.gz"
            with gzip.open(prediction_path,'wt',encoding='utf-8') as f:json.dump(rows,f,separators=(',',':'))
            metric_rows=[]
            for confidence in [p['metrics']['primary_confidence'],p['metrics']['secondary_confidence']]:
                for iou in p['metrics']['box_IoU_thresholds']:
                    metrics=compute_metrics(rows,confidence,iou);metrics['seed']=condition['seed'];metrics['orientation']=orientation
                    metric_rows.append(metrics)
            detail=out/f"seed{condition['seed']}_{orientation}_metrics.json";save(detail,metric_rows)
            result={'seed':condition['seed'],'orientation':orientation,'checkpoint_sha256':condition['sha256'],
                    'predictions_file':prediction_path.name,'predictions_sha256':sha(prediction_path),
                    'metrics_file':detail.name,'metrics_sha256':sha(detail),
                    'metrics':[{k:v for k,v in r.items() if k not in ['image_matches','by_date']} for r in metric_rows]}
            results.append(result);print(json.dumps(result),flush=True)
        assert sha(weight)==condition['sha256']
        del model;torch.cuda.empty_cache()
    # Date-cluster paired sensitivity only. Each date resample retains the
    # denominator of all repeated objects, rather than independent frame CIs.
    date_list=sorted(p['source_dates']);rng=np.random.default_rng(26);intervals=[]
    for seed in p['seeds']:
        metrics=[]
        for orientation in p['orientations']:
            rows=json.loads((out/f'seed{seed}_{orientation}_metrics.json').read_text())
            metrics.append(next(r for r in rows if r['confidence_threshold']==.2 and r['IoU_threshold']==.5))
        differences=np.array([metrics[1]['by_date'][d]['TP']-metrics[0]['by_date'][d]['TP'] for d in date_list])
        denominators=np.array([metrics[0]['by_date'][d]['GT'] for d in date_list])
        ix=rng.integers(0,len(date_list),size=(10000,len(date_list)))
        draws=differences[ix].sum(axis=1)/denominators[ix].sum(axis=1)
        lo,hi=np.quantile(draws,[.025,.975])
        intervals.append({'seed':seed,'original_recall':metrics[0]['recall'],'clockwise90_recall':metrics[1]['recall'],
                          'paired_recall_difference_90_minus_original':metrics[1]['recall']-metrics[0]['recall'],
                          'date_cluster_bootstrap95_percentile':[float(lo),float(hi)],'date_groups':len(date_list),
                          'resamples':10000,'scope':'exploratory date-cluster resampling, small number of dates; not source-video accuracy'})
    summary={'status':'FROZEN_THREE_SEED_PAIRED_ORIENTATION_VALIDATION_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
             'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ppath),
             'validation_images_per_condition':1571,'GT_objects_per_condition':1864,'conditions':results,
             'primary_paired_comparisons':intervals,'input_pixel_controls_sha256':sha(out/'input_pixel_controls.json'),
             'maximum_letterbox_pixel_rotation_difference':max(r['letterbox_rotated_max_uint8_difference'] for r in input_records),
             'GPU':torch.cuda.get_device_name(0),'torch':torch.__version__,'ultralytics':ultralytics.__version__,
             'elapsed_s':time.perf_counter()-timer,'new_training_updates':0,
             'source_Toros_or_candidate_final_images_opened':False,'source_video_count_failure_cause_proven':False,
             'whole_goal_complete':False}
    save(out/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='conditions'}),flush=True)


if __name__=='__main__':main()
