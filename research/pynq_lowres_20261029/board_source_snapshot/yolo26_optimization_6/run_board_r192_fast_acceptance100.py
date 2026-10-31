"""O6 attach-only reproducible full detector benchmark and camera demonstration."""
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
import pathlib,sys,argparse,time,json,fcntl,traceback,hashlib,resource
R=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--candidate',required=True);p.add_argument('--size',type=int,required=True);p.add_argument('--fixed',type=int,default=100);p.add_argument('--camera',type=int,default=0);p.add_argument('--warmups',type=int,default=3);p.add_argument('--tag',required=True);p.add_argument('--runtime',default='runtime');p.add_argument('--image');a=p.parse_args()
sys.path.insert(0,str(R/a.runtime))
import cv2,numpy as np
from native_ops import NativeOps
from hybrid_executor import YOLOHybridExecutor
from queue_conv import QueueConv
from board_runtime import preprocess,decode,annotate,stats
M=R/a.candidate/'model';out=R/'runs'/a.tag;out.mkdir(parents=True,exist_ok=False)
record=dict(status='RUNNING',candidate=a.candidate,resolution=a.size,runtime=a.runtime,fixed=[],camera=[],warmups=a.warmups,scope='total_ms=complete preprocess + entire actual inference + decode; initialization/capture/annotation/save separate',frame_age='sensor age and driver drops unmeasured',overlay_downloaded=False,failed_frames=0)
record['input_model_shape']=json.loads((M/'graph.json').read_text())['tensors']['images']['shape'];assert record['input_model_shape']==[1,3,a.size,a.size]
record['runtime_hashes']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (R/a.runtime).glob('*') if f.is_file()}
record['model_hashes']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in M.glob('*') if f.is_file()}
with pathlib.Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);cv2.setNumThreads(2);ex=be=cam=None
 try:
  init=time.perf_counter();native=NativeOps(R/a.runtime/'native_queue.so');be=QueueConv(M,native);ex=YOLOHybridExecutor(M,be,native,quantization_mode='fixed',fuse_activation=True,integer_routes=True);ex.enable_optimization('combined');record['initialization_ms']=(time.perf_counter()-init)*1000;record['overlay']=be.core.info
  def run(im):
   t=time.perf_counter();x=preprocess(im,a.size);u=time.perf_counter();raw=ex.run(x);v=time.perf_counter();boxes=decode(raw,im.shape,size=a.size);w=time.perf_counter()
   assert x.shape==(1,3,a.size,a.size) and raw.shape==(1,300,6) and np.isfinite(raw).all()
   s=be.core.status();assert s['error']=='0x0' and s['core']=='0x2' and all(int(s[k],16)&2 for k in ('MM2S','S2MM')),s
   item=dict(total_ms=(w-t)*1000,preprocess_ms=(u-t)*1000,inference_ms=(v-u)*1000,decode_ms=(w-v)*1000,detections=len(boxes),status=s)
   for k in ('packing_ms','DMA_FPGA_ms','unpack_ms','input_bytes','output_bytes','DDR_read_bytes','DDR_write_bytes'):item[k]=sum(q[k] for q in be.profile)
   item['PL_busy_ms']=sum(q['cycles'][0] for q in be.profile)/100000;item['PL_compute_ms']=sum(q['cycles'][3] for q in be.profile)/100000
   item['ARM_dispatch_residual_ms']=item['inference_ms']-item['packing_ms']-item['DMA_FPGA_ms']-item['unpack_ms'];item['head_worker_ms']=dict(ex.head_worker_ms)
   return raw,boxes,item
  image_path=pathlib.Path(a.image) if a.image else R/'test_images/bus.jpg';image=cv2.imread(str(image_path));assert image is not None
  record['image_path']=str(image_path);record['memory']=dict(input_tensor_bytes=3*a.size*a.size*4,constant_arrays_bytes=sum(v.nbytes for v in ex.constants.values()),packed_weight_bytes=sum(v.nbytes for v in be.weights.values()),PL_output_arrays_bytes=sum(v.nbytes for v in be.outputs.values()),persistent_CMA_bytes=be.core.info['CMA_bytes'],process_peak_RSS_KiB_after_init=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
  for _ in range(a.warmups):run(image)
  golden=None
  with (out/'samples.jsonl').open('x') as stream:
   for i in range(a.fixed):
    raw,boxes,item=run(image)
    if golden is None:golden=raw.copy()
    else:assert golden.tobytes()==raw.tobytes(),'Fixed-frame raw instability'
    item['index']=i;record['fixed'].append(item);stream.write(json.dumps(dict(kind='fixed',**item))+'\n');stream.flush()
    if i==0:
     cv2.imwrite(str(out/'bus_detections.jpg'),annotate(image,boxes));np.save(out/'bus_raw.npy',raw);(out/'bus_boxes.json').write_text(json.dumps(boxes.tolist()))
    print('O6_FIXED',a.tag,i+1,round(item['total_ms'],3),len(boxes),flush=True)
   record['process_peak_RSS_KiB_after_fixed']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
   (out/'result.json').write_text(json.dumps(record,indent=2))
   if a.camera:
    cam=cv2.VideoCapture(0,cv2.CAP_V4L2);cam.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'));cam.set(cv2.CAP_PROP_FRAME_WIDTH,640);cam.set(cv2.CAP_PROP_FRAME_HEIGHT,480);assert cam.isOpened()
    record['camera_format']=dict(width=cam.get(cv2.CAP_PROP_FRAME_WIDTH),height=cam.get(cv2.CAP_PROP_FRAME_HEIGHT),FPS=cam.get(cv2.CAP_PROP_FPS),fourcc=int(cam.get(cv2.CAP_PROP_FOURCC)))
    start=time.perf_counter()
    for i in range(a.camera):
     t=time.perf_counter();ok,im=cam.read();u=time.perf_counter();assert ok and im is not None
     raw,boxes,item=run(im);v=time.perf_counter();drawn=annotate(im,boxes);w=time.perf_counter();item.update(index=i,capture_ms=(u-t)*1000,annotate_ms=(w-v)*1000,save_ms=0.)
     if i in (0,a.camera-1):
      cv2.imwrite(str(out/('camera_%03d_input.jpg'%i)),im);cv2.imwrite(str(out/('camera_%03d_detections.jpg'%i)),drawn);np.save(out/('camera_%03d_raw.npy'%i),raw);(out/('camera_%03d_boxes.json'%i)).write_text(json.dumps(boxes.tolist()));item['save_ms']=(time.perf_counter()-w)*1000
     item['capture_through_save_ms']=(time.perf_counter()-t)*1000;record['camera'].append(item);stream.write(json.dumps(dict(kind='camera',**item))+'\n');stream.flush();print('O6_CAMERA',a.tag,i+1,round(item['total_ms'],3),len(boxes),flush=True)
    record['camera_wall_FPS']=a.camera/(time.perf_counter()-start)
  keys=('total_ms','preprocess_ms','inference_ms','decode_ms','packing_ms','DMA_FPGA_ms','unpack_ms','PL_busy_ms','PL_compute_ms','ARM_dispatch_residual_ms')
  for kind in ('fixed','camera'):
   if record[kind]:record[kind+'_statistics']={k:stats([x[k] for x in record[kind]]) for k in keys}
  captures={};original=be.execute
  def capture(x,w,b,s,c):
   y=original(x,w,b,s,c);captures['input_%d'%s['id']]=x.copy();captures['output_%d'%s['id']]=y.copy();return y
  be.execute=capture;raw,boxes,item=run(image);be.execute=original;np.savez_compressed(out/'actual_PL.npz',**captures)
  record['diagnostic']=dict(nodes=ex.profile.copy(),layers=be.profile.copy(),head_worker_ms=ex.head_worker_ms.copy());record.update(status='O6_BOARD_TEST_PASS',successful_fixed=len(record['fixed']),successful_camera=len(record['camera']),DMA_errors=0,DMA_hangs=0,final_status=be.core.status())
 except Exception as e:record.update(status='FAILED',failed_frames=record['failed_frames']+1,error=repr(e),traceback=traceback.format_exc());raise
 finally:
  if cam:cam.release()
  try:
   if ex:ex.close()
  finally:
   if be:be.close();record['buffers_freed']=bool(be.core.tx.freed and be.core.rx.freed)
   record['process_peak_RSS_KiB_final']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
   (out/'result.json').write_text(json.dumps(record,indent=2))
print(record['status'],a.tag,record.get('fixed_statistics',{}).get('total_ms'),flush=True)
