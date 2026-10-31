"""Evaluate actual final FPGA integer arithmetic on PC; timings are NOT board E2E."""
import os
os.environ['OMP_NUM_THREADS']='4'
import pathlib,sys,json,argparse,time,hashlib
D=pathlib.Path(__file__).resolve().parent;R=D.parent;P=D
sys.path[:0]=[str(R/'envs/stage_d_pc_extras'),str(D/'pc_runtime_original'),str(D/'runtime')]
if '--lut' in sys.argv:sys.path.insert(0,str(D/'pc_runtime_lut'))
if '--fast' in sys.argv:sys.path.insert(0,str(D/'pc_runtime_fast'))
import torch,cv2,numpy as np
from hybrid_executor import YOLOHybridExecutor
from integer_backend import TorchIntegerBackend
import importlib.util
bs=importlib.util.spec_from_file_location('o6_board_runtime',D/'runtime/board_runtime.py');br=importlib.util.module_from_spec(bs);bs.loader.exec_module(br)
preprocess,decode,annotate=br.preprocess,br.decode,br.annotate
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--size',type=int,required=True);p.add_argument('--limit',type=int,default=100);p.add_argument('--label',default='screen100');p.add_argument('--lut',action='store_true');p.add_argument('--fast',action='store_true');p.add_argument('--images',required=True);p.add_argument('--annotations',required=True);p.add_argument('--output',required=True);a=p.parse_args()
MROOT=D/a.candidate;O=pathlib.Path(a.output).resolve();O.mkdir(parents=True,exist_ok=False)
torch.set_num_threads(4);cv2.setNumThreads(4)
ex=YOLOHybridExecutor(MROOT/'model',TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)
ann=pathlib.Path(a.annotations);images=pathlib.Path(a.images);coco=COCO(str(ann));cats=sorted(coco.getCatIds())
ids=json.loads((D/'dataset_split.json').read_text())['validation'][:a.limit];pred=[];start=time.perf_counter()
with (O/'per_image.jsonl').open('x') as log:
 for i,id in enumerate(ids):
  im=cv2.imread(str(images/coco.imgs[id]['file_name']));assert im is not None
  t=time.perf_counter();raw=ex.run(preprocess(im,a.size));dt=(time.perf_counter()-t)*1000
  assert raw.shape==(1,300,6) and np.isfinite(raw).all()
  boxes=decode(raw,im.shape,threshold=.001,size=a.size)
  for x0,y0,x1,y1,s,c in boxes:pred.append(dict(image_id=int(id),category_id=cats[int(c)],bbox=[float(x0),float(y0),float(x1-x0),float(y1-y0)],score=float(s)))
  log.write(json.dumps(dict(index=i,image_id=id,PC_inference_ms=dt,detections_at_0001=len(boxes)))+'\n');log.flush()
  if i<5:cv2.imwrite(str(O/('%012d.jpg'%id)),annotate(im,decode(raw,im.shape,size=a.size)))
  if (i+1)%50==0:print('O6_PC_ACCURACY',a.candidate,i+1,len(ids),'elapsed_s',round(time.perf_counter()-start,2),flush=True)
(O/'predictions.json').write_text(json.dumps(pred))
if pred:
 ev=COCOeval(coco,coco.loadRes(pred),'bbox');ev.params.imgIds=ids;ev.evaluate();ev.accumulate();ev.summarize();metrics=ev.stats.tolist()
else:metrics=[0.]*12
record=dict(status='COCO5000_COMPLETE' if len(ids)==5000 else 'SUBSET_SCREEN_NOT_FORMAL_COCO5000',candidate=a.candidate,resolution=a.size,images=len(ids),AP50_95_percent=metrics[0]*100,AP50_percent=metrics[1]*100,COCO_stats=metrics,duration_s=time.perf_counter()-start,annotation_sha256=hashlib.sha256(ann.read_bytes()).hexdigest(),model_graph_sha256=hashlib.sha256((MROOT/'model/graph.json').read_bytes()).hexdigest(),scope='PC final integer-valued exact Conv/fixed requant/LUT plus CPU FP32 partitions; not board speed and not board5000')
(O/'metrics.json').write_text(json.dumps(record,indent=2));print('O6_PC_EVAL_COMPLETE',record,flush=True)
