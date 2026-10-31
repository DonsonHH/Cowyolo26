"""O8 normal entry: verified artifacts, resident execution, no FPGA download."""
import os,sys,pathlib,argparse,time,json,fcntl
os.environ['OMP_NUM_THREADS']='2';sys.dont_write_bytecode=True
R=pathlib.Path(__file__).resolve().parent;sys.path[:0]=[str(R),str(R/'runtime_fast')]
import numpy as np,cv2
from verify_release import verify
from native_graph import NativeGraph
from board_runtime import decode,annotate,stats,NAMES
def main():
 p=argparse.ArgumentParser();p.add_argument('--profile',choices=('fast192','flagship224','quality256'),default='flagship224');p.add_argument('--image',type=pathlib.Path);p.add_argument('--camera',action='store_true');p.add_argument('--frames',type=int,default=10);p.add_argument('--threshold',type=float,default=.25);a=p.parse_args();verify(R);size={'fast192':192,'flagship224':224,'quality256':256}[a.profile];cv2.setNumThreads(2)
 L=pathlib.Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock');L.parent.mkdir(parents=True,exist_ok=True);lock=L.open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);O=R/'runs'/('demo_'+str(time.time_ns()));O.mkdir(parents=True,exist_ok=False);g=None;cap=None;records=[];init=time.perf_counter()
 try:
  from device_initialize import initialize
  device_initialization=initialize(R);selected=json.loads((R/'selected_candidates.json').read_text())[str(size)]
  g=NativeGraph(size,options=selected['options'],plan=selected['plan'],firmware_manifest='hardware/accepted/firmware_manifest.json');initialization_ms=(time.perf_counter()-init)*1000
  if a.camera:
   cap=cv2.VideoCapture('/dev/video0',cv2.CAP_V4L2);assert cap.isOpened();cap.set(cv2.CAP_PROP_FOURCC,cv2.VideoWriter_fourcc(*'MJPG'));cap.set(cv2.CAP_PROP_FRAME_WIDTH,640);cap.set(cv2.CAP_PROP_FRAME_HEIGHT,480);cap.set(cv2.CAP_PROP_BUFFERSIZE,1)
  for i in range(a.frames if a.camera else 1):
   ct=time.perf_counter()
   if cap:ok,image=cap.read();assert ok,'camera capture failed'
   else:image=cv2.imread(str(a.image or R/'test_images/bus.jpg'));assert image is not None
   capture_or_read_ms=(time.perf_counter()-ct)*1000;start=time.perf_counter();raw=g.run_image(image);boxes=decode(raw,image.shape,a.threshold,size);e2e_ms=(time.perf_counter()-start)*1000
   sv=time.perf_counter();cv2.imwrite(str(O/f'{i:04d}_original.jpg'),image);cv2.imwrite(str(O/f'{i:04d}_detected.jpg'),annotate(image,boxes));np.save(O/f'{i:04d}_raw.npy',raw);np.save(O/f'{i:04d}_boxes.npy',boxes);save_ms=(time.perf_counter()-sv)*1000
   detections=[dict(box=list(map(float,b[:4])),score=float(b[4]),class_id=int(b[5]),class_name=NAMES[int(b[5])]) for b in boxes];record=dict(index=i,E2E_ms=e2e_ms,capture_or_read_ms=capture_or_read_ms,annotate_save_ms=save_ms,detections=detections,status=g.status());records.append(record);print(json.dumps(record,ensure_ascii=False),flush=True)
  result=dict(profile=a.profile,input_size=size,initialization_ms=initialization_ms,device_initialization=device_initialization,selected=selected,cold_first_frame_ms=records[0]['E2E_ms'],records=records,summary=stats([v['E2E_ms'] for v in records]),scope='Complete board preprocess/native inference/detection decode. Cold demo is not warmed100 benchmark. Camera frame age unmeasured.');(O/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('RESULT_DIRECTORY',O,flush=True)
 finally:
  if cap:cap.release()
  if g:g.close()
if __name__=='__main__':main()
