"""Board preprocessing, NMS-free decoding, drawing and profile accounting."""
import pathlib,json,time,collections
import numpy as np,cv2
ROOT=pathlib.Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d')
NAMES='person bicycle car motorcycle airplane bus train truck boat traffic_light fire_hydrant stop_sign parking_meter bench bird cat dog horse sheep cow elephant bear zebra giraffe backpack umbrella handbag tie suitcase frisbee skis snowboard sports_ball kite baseball_bat baseball_glove skateboard surfboard tennis_racket bottle wine_glass cup fork knife spoon bowl banana apple sandwich orange broccoli carrot hot_dog pizza donut cake chair couch potted_plant bed dining_table toilet tv laptop mouse remote keyboard cell_phone microwave oven toaster sink refrigerator book clock vase scissors teddy_bear hair_drier toothbrush'.split()
def preprocess(image):
    h,w=image.shape[:2];gain=min(640/h,640/w);nw,nh=round(w*gain),round(h*gain)
    resized=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR) if (nw,nh)!=(w,h) else image
    dx=(640-nw)/2;dy=(640-nh)/2
    padded=cv2.copyMakeBorder(resized,round(dy-.1),round(dy+.1),round(dx-.1),round(dx+.1),cv2.BORDER_CONSTANT,value=(114,114,114))
    return np.ascontiguousarray(padded[...,::-1].transpose(2,0,1)[None],dtype=np.float32)/np.float32(255)
def decode(raw,image_shape,threshold=.25):
    boxes=raw[0,raw[0,:,4]>=threshold].copy();h,w=image_shape[:2];gain=min(640/h,640/w)
    px=round((640-w*gain)/2-.1);py=round((640-h*gain)/2-.1)
    boxes[:,[0,2]]=(boxes[:,[0,2]]-px)/gain;boxes[:,[1,3]]=(boxes[:,[1,3]]-py)/gain
    boxes[:,[0,2]]=np.clip(boxes[:,[0,2]],0,w);boxes[:,[1,3]]=np.clip(boxes[:,[1,3]],0,h)
    return boxes
def annotate(image,boxes):
    result=image.copy()
    for x0,y0,x1,y1,score,cls in boxes:
        c=int(cls);color=((37*c+40)%220+35,(71*c+40)%220+35,(109*c+40)%220+35)
        cv2.rectangle(result,(int(x0),int(y0)),(int(x1),int(y1)),color,2)
        cv2.putText(result,'%s %.2f'%(NAMES[c],score),(int(x0),max(18,int(y0)-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,1,cv2.LINE_AA)
    return result
def stats(values):
    a=np.asarray(values,dtype=np.float64)
    return dict(mean=float(a.mean()),median=float(np.median(a)),min=float(a.min()),max=float(a.max()),p95=float(np.percentile(a,95)))
def summarize(executor,backend):
    ops=collections.defaultdict(float)
    for item in executor.profile:ops[item['op']]+=item['ms']
    samples=[s for layer in backend.profile for s in layer['samples']]
    sums={name:sum(s[name] for s in samples) for name in ('packing_ms','DMA_FPGA_ms','unpack_ms','input_bytes','output_bytes')}
    cycles=np.sum([s['cycles'] for s in samples],axis=0).tolist()
    sums.update(commands=len(samples),weight_cache_hits=sum(s.get('weight_reuse',False) for s in samples),cycles=cycles,
        FPGA_compute_ms=cycles[3]/100000,FPGA_busy_ms=cycles[0]/100000,overlap_ms=cycles[9]/100000,
        CPU_operators_ms=sum(v for k,v in ops.items() if k!='QuantConv'),operator_ms=dict(ops))
    return sums
def make_executor(weight_cache=True,overlap=True,fuse_activation=True,native_submission=True,model_name='model_final'):
    from native_ops import NativeOps
    from quantized_conv import QuantizedConv
    from hybrid_executor import YOLOHybridExecutor
    native=NativeOps(ROOT/'native_runtime.so');backend=QuantizedConv(ROOT/model_name,native,overlap=overlap,native_submission=native_submission,weight_cache=weight_cache)
    executor=YOLOHybridExecutor(ROOT/model_name,backend,native,quantization_mode='fixed',fuse_activation=fuse_activation)
    return executor,backend
