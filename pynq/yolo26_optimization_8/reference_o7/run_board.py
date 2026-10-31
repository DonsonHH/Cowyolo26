"""O7 board benchmark: complete preprocess+native graph+decode; no programming."""
import os,sys,pathlib,argparse,time,json,hashlib,fcntl,resource,traceback
os.environ['OMP_NUM_THREADS']='2';sys.dont_write_bytecode=True;resource.setrlimit(resource.RLIMIT_CORE,(0,0))
R=pathlib.Path(__file__).resolve().parent;sys.path[:0]=[str(R),str(R/'runtime_fast')]
import numpy as np,cv2
from native_graph import NativeGraph
from board_runtime import decode,annotate,stats
def main():
 p=argparse.ArgumentParser();p.add_argument('--size',type=int,default=224);p.add_argument('--fixed',type=int,default=100);p.add_argument('--camera',type=int,default=100);p.add_argument('--warmups',type=int,default=3);p.add_argument('--output',required=True);a=p.parse_args();O=pathlib.Path(a.output);O.mkdir(parents=True,exist_ok=False);cv2.setNumThreads(2)
 lock=open('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);g=None;cap=None;records=[];result=dict(size=a.size,scope='board complete preprocess/inference/decode; initialization/capture/drawing/saving separate',fixed=[],camera=[],warmups=[],failed=0)
 def memory():return pathlib.Path('/proc/meminfo').read_text()
 result['memory_before']=memory()
 try:
  start=time.perf_counter();g=NativeGraph(a.size);result['initialization_ms']=(time.perf_counter()-start)*1000;result['status_before']=g.status();image=cv2.imread(str(R/'test_images/bus.jpg'));assert image is not None
  def one(im,phase,index):
   st=time.perf_counter();raw=g.run_image(im);before_decode=time.perf_counter();boxes=decode(raw,im.shape,size=a.size);end=time.perf_counter();tim=g.timers
   py_pre=g.last_python_preprocess_ms
   item=dict(phase=phase,index=index,total_ms=(end-st)*1000,preprocess_python_ms=py_pre,preprocess_ms=py_pre+float(tim[10]),inference_ms=float(tim[7]-tim[10]),host_bridge_ms=(before_decode-st)*1000-py_pre-float(tim[7]),native_initial_quant_ms=float(tim[10]),native_graph_total_ms=float(tim[7]),decode_ms=(end-before_decode)*1000,packing_ms=float(tim[0]),DMA_FPGA_wait_ms=float(tim[1]),unpack_ms=float(tim[2]),PL_busy_ms=float(tim[3]),PL_compute_ms=float(tim[4]),ARM_dispatch_residual_ms=float(tim[5]-tim[10]),depthwise_ms=float(tim[6]),DMA_TX_bytes=int(tim[8]),DMA_RX_bytes=int(tim[9]),DDR_read_bytes=int(tim[11]),DDR_write_bytes=int(tim[12]),detections=len(boxes),status=g.status())
   assert np.isfinite(raw).all() and raw.shape==(1,300,6);assert item['status']['error']=='0x0' and item['status']['MM2S']=='0x1002' and item['status']['S2MM']=='0x1002'
   if phase in ('fixed','warmup'):item['raw_bitexact_cold']=bool(np.array_equal(raw,cold_raw));assert item['raw_bitexact_cold']
   log.write(json.dumps(item)+'\n');log.flush();return raw,boxes,item
  with (O/'per_frame.jsonl').open('x') as log:
   raw,boxes,item=one(image,'cold',0);cold_raw=raw.copy();result['cold_first_frame']=item;np.save(O/'cold_raw.npy',raw);cv2.imwrite(str(O/'bus_detected.jpg'),annotate(image,boxes));np.save(O/'bus_boxes.npy',boxes)
   for i in range(a.warmups):raw,boxes,item=one(image,'warmup',i);result['warmups'].append(item)
   for i in range(a.fixed):
    raw,boxes,item=one(image,'fixed',i);result['fixed'].append(item)
    if (i+1)%20==0:print('O7_FIXED',a.size,i+1,item['total_ms'],flush=True)
   np.save(O/'fixed_last_raw.npy',raw);np.save(O/'node_ms.npy',g.profile)
   blocks={}
   for n in g.meta['nodes']:
    if n['op'] in ('QuantConv','Depthwise'):
     sid=n['attrs'][0];blocks[f'input{sid}']=g.tensor(n['inputs'][0]);blocks[f'output{sid}']=g.tensor(n['outputs'][0])
   np.savez_compressed(O/'actual_blocks.npz',**blocks)
   if a.camera:
    cap=cv2.VideoCapture('/dev/video0',cv2.CAP_V4L2);assert cap.isOpened();cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'));cap.set(cv2.CAP_PROP_FRAME_WIDTH,640);cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480);cap.set(cv2.CAP_PROP_FPS,30);cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
    result['camera_device']=dict(device='/dev/video0',fourcc=int(cap.get(cv2.CAP_PROP_FOURCC)),width=cap.get(cv2.CAP_PROP_FRAME_WIDTH),height=cap.get(cv2.CAP_PROP_FRAME_HEIGHT),nominal_fps=cap.get(cv2.CAP_PROP_FPS),frame_age='not measured')
    wall=time.perf_counter()
    for i in range(a.camera):
     ct=time.perf_counter();ok,im=cap.read();capture_ms=(time.perf_counter()-ct)*1000
     if not ok:result['failed']+=1;log.write(json.dumps(dict(phase='camera',index=i,capture_failed=True))+'\n');log.flush();continue
     raw,boxes,item=one(im,'camera',i);item['capture_ms']=capture_ms;result['camera'].append(item)
     if i in (0,24,49,74,99):
      sv=time.perf_counter();cv2.imwrite(str(O/f'camera_{i:03d}_original.png'),im);cv2.imwrite(str(O/f'camera_{i:03d}_detected.jpg'),annotate(im,boxes));np.save(O/f'camera_{i:03d}_boxes.npy',boxes);np.save(O/f'camera_{i:03d}_raw.npy',raw);item['draw_save_ms']=(time.perf_counter()-sv)*1000
     if (i+1)%20==0:print('O7_CAMERA',a.size,i+1,item['total_ms'],flush=True)
    result['camera_wall_s']=time.perf_counter()-wall;result['camera_wall_FPS']=len(result['camera'])/result['camera_wall_s'];cap.release();cap=None
    arrays={}
    for n in g.meta['nodes']:
     if n['op'] in ('QuantConv','Depthwise'):
      sid=n['attrs'][0];arrays[f'input{sid}']=g.tensor(n['inputs'][0]);arrays[f'output{sid}']=g.tensor(n['outputs'][0])
    np.savez_compressed(O/'camera_last_actual_blocks.npz',**arrays)
  for phase in ('fixed','camera'):
   values=result[phase]
   if values:result[phase+'_statistics']={k:stats([v[k] for v in values]) for k in ('total_ms','preprocess_ms','inference_ms','host_bridge_ms','decode_ms','packing_ms','DMA_FPGA_wait_ms','unpack_ms','PL_busy_ms','PL_compute_ms','ARM_dispatch_residual_ms','depthwise_ms','native_initial_quant_ms')}
  result['memory_usage']=g.memory();result['status_after']=g.status();result['library_sha256']=hashlib.sha256((R/'native_sources/native_queue.so').read_bytes()).hexdigest();result['program_sha256']=hashlib.sha256((R/f'program_r{a.size}/graph.bin').read_bytes()).hexdigest();result['status']='PASS' if len(result['fixed'])==a.fixed and len(result['camera'])==a.camera and not result['failed'] else 'FAIL'
 except BaseException:
  result['status']='FAIL';result['failure']=traceback.format_exc();(O/'failure.txt').write_text(result['failure']);raise
 finally:
  if cap:cap.release()
  if g:g.close()
  result['memory_after_close']=memory();(O/'summary.json').write_text(json.dumps(result,indent=2));print('O7_RUN_OUTPUT',str(O),result['status'],flush=True)
if __name__=='__main__':main()
