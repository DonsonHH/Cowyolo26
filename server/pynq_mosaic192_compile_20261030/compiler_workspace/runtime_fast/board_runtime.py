"""Board preprocessing, NMS-free decoding, drawing and profile accounting."""
import pathlib,json,time,collections
import numpy as np,cv2
ROOT=pathlib.Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d')
NAMES='person bicycle car motorcycle airplane bus train truck boat traffic_light fire_hydrant stop_sign parking_meter bench bird cat dog horse sheep cow elephant bear zebra giraffe backpack umbrella handbag tie suitcase frisbee skis snowboard sports_ball kite baseball_bat baseball_glove skateboard surfboard tennis_racket bottle wine_glass cup fork knife spoon bowl banana apple sandwich orange broccoli carrot hot_dog pizza donut cake chair couch potted_plant bed dining_table toilet tv laptop mouse remote keyboard cell_phone microwave oven toaster sink refrigerator book clock vase scissors teddy_bear hair_drier toothbrush'.split()
def preprocess(image,size=640):
    h,w=image.shape[:2];gain=min(size/h,size/w);nw,nh=round(w*gain),round(h*gain)
    resized=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR) if (nw,nh)!=(w,h) else image
    dx=(size-nw)/2;dy=(size-nh)/2
    padded=cv2.copyMakeBorder(resized,round(dy-.1),round(dy+.1),round(dx-.1),round(dx+.1),cv2.BORDER_CONSTANT,value=(114,114,114))
    return np.ascontiguousarray(padded[...,::-1].transpose(2,0,1)[None],dtype=np.float32)/np.float32(255)
def decode(raw,image_shape,threshold=.25,size=640):
    boxes=raw[0,raw[0,:,4]>=threshold].copy();h,w=image_shape[:2];gain=min(size/h,size/w)
    px=round((size-w*gain)/2-.1);py=round((size-h*gain)/2-.1)
    boxes[:,[0,2]]=(boxes[:,[0,2]]-px)/gain;boxes[:,[1,3]]=(boxes[:,[1,3]]-py)/gain
    boxes[:,[0,2]]=np.clip(boxes[:,[0,2]],0,w);boxes[:,[1,3]]=np.clip(boxes[:,[1,3]],0,h)
    return boxes
def annotate(image,boxes):
    result=image.copy()
    for x0,y0,x1,y1,score,cls in boxes:
        c=int(cls);color=((37*c+70)%156+100,(71*c+70)%156+100,(109*c+70)%156+100)
        cv2.rectangle(result,(int(x0),int(y0)),(int(x1),int(y1)),color,2)
        text='%s %.2f'%(NAMES[c],score);font=cv2.FONT_HERSHEY_SIMPLEX;scale=.6
        (tw,th),baseline=cv2.getTextSize(text,font,scale,1);lx=max(0,min(int(x0),result.shape[1]-tw-8));ly=max(th+6,int(y0)-6)
        cv2.rectangle(result,(lx,ly-th-5),(lx+tw+7,ly+baseline+2),(15,15,15),-1)
        cv2.putText(result,text,(lx+3,ly),font,scale,(255,255,255),1,cv2.LINE_AA)
    return result
def stats(values):
    a=np.asarray(values,dtype=np.float64)
    return dict(mean=float(a.mean()),median=float(np.median(a)),min=float(a.min()),max=float(a.max()),p95=float(np.percentile(a,95)))
