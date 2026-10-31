from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,gzip,os,math
from collections import Counter,defaultdict
import cv2,numpy as np,torch
from ultralytics import YOLO
from geometry import assign,ious
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/pairs'
def load(p):return json.loads(p.read_text())
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/'protocol/input_controls_v1.json');assert p['main_protocol_sha256']==sha(ROOT/'protocol/pairs_v1.json')
assert torch.cuda.is_available() and os.environ.get('SLURM_JOB_ID');cv2.setNumThreads(1);torch.set_num_threads(4);torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
images=loadgz(OUT/'source_geometry.json.gz')['val'];images={r['file_name']:r for r in images}
dest=ROOT/'results/input_controls';dest.mkdir(exist_ok=False);rows=[];tensor_records=[];num=0;coordinate_maxdelta=0.;regressions=[];shapes=Counter()
for condition in p['models']:
    checkpoint=Path(condition['checkpoint']);assert sha(checkpoint)==condition['sha256'];model=YOLO(str(checkpoint));cow=[k for k,v in model.names.items() if v=='cow'];assert len(cow)==1
    active={}
    def start(predictor):
        if getattr(predictor,'_controls_hooked',False):return
        original=predictor.inference
        def inference(im,*args,**kwargs):
            tensor=im.detach().cpu().contiguous().numpy();record={**active,'tensor_shape':list(im.shape),'tensor_sha256':hashlib.sha256(tensor.tobytes()).hexdigest()}
            tensor_records.append(record);shapes[str(tuple(im.shape))]+=1
            return original(im,*args,**kwargs)
        predictor.inference=inference;predictor._controls_hooked=True
    model.add_callback('on_predict_start',start)
    main={r['file_name']:r for r in loadgz(OUT/('val_'+condition['name']+'_predictions.json.gz'))}
    previous={}
    if condition['seed'] is not None:
        for orient in ['original','clockwise90']:
            file=ROOT.parent/'orientation_validation_20261027/results/control'/('seed'+str(condition['seed'])+'_'+orient+'_predictions.json.gz')
            previous[orient]={r['file_name']:r for r in loadgz(file)}
    for ci,config in enumerate(p['configurations']):
        group=[]
        for filename in p['sample_names']:
            row=images[filename];file=Path(row['image_alias']);assert sha(file)==row['sha256']
            native=cv2.imread(str(file));assert native.shape==(720,1280,3)
            rotated=config['orientation']=='clockwise90';image=np.rot90(native,k=-1).copy() if rotated else native
            active={'condition':condition['name'],'config_index':ci,'file_name':filename}
            result=model.predict(image,imgsz=config['imgsz'],rect=config['rect'],batch=1,conf=.2,iou=.5,classes=cow,max_det=300,half=False,augment=False,device=0,verbose=False)[0];num+=1
            boxes=result.boxes.xyxy.detach().cpu().numpy().astype(float);conf=result.boxes.conf.detach().cpu().numpy().astype(float)
            if rotated:back=np.asarray([[y1,720-x2,y2,720-x1] for x1,y1,x2,y2 in boxes],dtype=float).reshape(-1,4)
            else:back=boxes
            reference_native=[r['visible_reference_AABB'] for r in row['references']]
            reference_current=[[720-y2,x1,720-y1,x2] for x1,y1,x2,y2 in reference_native] if rotated else reference_native
            matches,native_iou=assign(reference_native,back.tolist());_,current_iou=assign(reference_current,boxes.tolist())
            delta=float(np.max(np.abs(native_iou-current_iou))) if native_iou.size else 0.;coordinate_maxdelta=max(coordinate_maxdelta,delta);assert delta<1e-10
            predictions=[{'native_xyxy':b.tolist(),'current_xyxy':a.tolist(),'confidence':float(c)} for a,b,c in zip(boxes,back,conf)]
            entry={'condition':condition['name'],'config_index':ci,'config':config,'file_name':filename,'source_sha256':row['sha256'],
            'references':len(row['references']),'predictions':predictions,'matched':len(matches),'unmatched_references':len(row['references'])-len(matches),
            'unmatched_predictions':len(predictions)-len(matches),'coordinate_IoU_invariance_delta':delta}
            if ci in [0,8]:
                old=main[filename]['predictions'];assert len(old)==len(predictions)
                errors=[max(abs(x-y) for x,y in zip(a['native_xyxy'],b['native_xyxy'])) for a,b in zip(old,predictions)]
                cerrors=[abs(a['confidence']-b['confidence']) for a,b in zip(old,predictions)]
                assert max(errors,default=0)<1e-4 and max(cerrors,default=0)<1e-4
                regressions.append({'condition':condition['name'],'file_name':filename,'config_index':ci,'main_box_maxdelta':max(errors,default=0),'confidence_maxdelta':max(cerrors,default=0)})
            if previous and config['imgsz']==320 and config['rect'] is False:
                old=[r for r in previous[config['orientation']][filename]['predictions'] if r['confidence']>=.2]
                cross,_=assign([r['xyxy'] for r in old],boxes.tolist(),threshold=.999)
                entry['prior320_square_regression']={'prior_count':len(old),'current_count':len(predictions),'IoU0999matched':len(cross),
                'all_boxes_correspond':len(cross)==len(old)==len(predictions)}
            rows.append(entry);group.append(entry)
        print(json.dumps({'condition':condition['name'],'config':config,'GT':sum(r['references'] for r in group),'TP':sum(r['matched'] for r in group),
            'unmatched_predictions':sum(r['unmatched_predictions'] for r in group)}),flush=True)
    assert sha(checkpoint)==condition['sha256'];del model;torch.cuda.empty_cache()
assert num==len(tensor_records)==288
metrics=[]
for condition in p['models']:
    for ci,config in enumerate(p['configurations']):
        subset=[r for r in rows if r['condition']==condition['name'] and r['config_index']==ci]
        metrics.append({'condition':condition['name'],'config_index':ci,**config,'images':len(subset),'references':sum(r['references'] for r in subset),
            'matched':sum(r['matched'] for r in subset),'unmatched_references':sum(r['unmatched_references'] for r in subset),
            'unmatched_predictions':sum(r['unmatched_predictions'] for r in subset)})
summary={'status':'EIGHT_FIXED_SOURCE_IMAGES_ALL4_MODELS_INPUT_FACTORIAL288_FORWARDS_AND64_BASELINE_REPEATS_COMPLETE',
'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/input_controls_v1.json'),
'actual_source_image_forwards':num,'coordinate_IoU_invariance_maxdelta':coordinate_maxdelta,'main_first_last_repeat_cases':len(regressions),
'metrics':metrics,'tensor_shape_counts':dict(shapes),'new_training_updates':0,'whole_goal_complete':False}
for name,data in [('rows.json',rows),('tensor_records.json',tensor_records),('baseline_regressions.json',regressions),('summary.json',summary)]:
    out=dest/name;assert not out.exists();out.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='metrics'}),flush=True)
