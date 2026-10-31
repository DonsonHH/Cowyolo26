import pathlib,json,sys,time
import numpy as np,cv2
ROOT=pathlib.Path(__file__).resolve().parents[2]
# Dependencies are provided by this package's pc_lib and pinned environment.
from common import preprocess,session
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

def boxes_from_raw(raw,image_shape,threshold=.001):
    boxes=raw[0,raw[0,:,4]>=threshold].copy()
    h,w=image_shape[:2];gain=min(640/h,640/w)
    px=round((640-w*gain)/2-.1);py=round((640-h*gain)/2-.1)
    boxes[:,[0,2]]=(boxes[:,[0,2]]-px)/gain;boxes[:,[1,3]]=(boxes[:,[1,3]]-py)/gain
    boxes[:,[0,2]]=np.clip(boxes[:,[0,2]],0,w);boxes[:,[1,3]]=np.clip(boxes[:,[1,3]],0,h)
    return boxes
def evaluate_images(predictor,annotation,image_root,ids,progress=False):
    coco=COCO(str(annotation));categories=sorted(coco.getCatIds());predictions=[];times=[]
    for index,image_id in enumerate(ids):
        image=coco.imgs[image_id];array=cv2.imread(str(pathlib.Path(image_root)/image['file_name']))
        if array is None:raise FileNotFoundError(image['file_name'])
        x=preprocess(array);start=time.perf_counter();raw=predictor(x);times.append((time.perf_counter()-start)*1000)
        for row in boxes_from_raw(raw,array.shape):
            x0,y0,x1,y1,score,category=row
            predictions.append({'image_id':int(image_id),'category_id':categories[int(category)],'bbox':[float(x0),float(y0),float(x1-x0),float(y1-y0)],'score':float(score)})
        if progress and (index+1)%100==0:print('ACCURACY_PROGRESS',index+1,'/',len(ids),'inference_ms',round(float(np.mean(times[-100:])),2),flush=True)
    if predictions:
        detections=coco.loadRes(predictions);evaluator=COCOeval(coco,detections,'bbox');evaluator.params.imgIds=ids
        evaluator.evaluate();evaluator.accumulate();evaluator.summarize()
        stats=evaluator.stats.tolist()
        # Operating precision/recall at score0.25, IoU0.5, all area, maxDet100.
        records=[r for r in evaluator.evalImgs if r is not None and r['aRng']==[0,10000000000.0] and r['maxDet']==100]
        tp=fp=gt=0
        for record in records:
            selected=np.asarray(record['dtScores'])>=.25;valid=~record['dtIgnore'][0]
            tp+=int(np.count_nonzero(selected&valid&(record['dtMatches'][0]>0)))
            fp+=int(np.count_nonzero(selected&valid&(record['dtMatches'][0]==0)))
            gt+=int(np.count_nonzero(~np.asarray(record['gtIgnore'],dtype=bool)))
        precision=tp/max(tp+fp,1);recall=tp/max(gt,1)
    else:stats=[0.0]*12;precision=recall=0
    return {'images':len(ids),'mAP50_95':stats[0],'mAP50':stats[1],'COCO_stats':stats,'precision_at_conf025_iou05':precision,
            'recall_at_conf025_iou05':recall,'operating_metric_scope':'COCO crowd/ignore handling, all areas, maxDet100, score>=0.25, IoU0.5',
            'mean_inference_ms':float(np.mean(times))},predictions
