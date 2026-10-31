"""Actual O8 graph plus actual ARM tracker/counters on every frozen video input."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,time,hashlib,gzip,fcntl,traceback
os.environ['XILINX_XRT']='/usr';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np,cv2
from pynq import PL
ROOT=Path(__file__).resolve().parent
O8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8')
PORT=Path('/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029')
MODEL=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_rot192_qual_20261029')
sys.path[:0]=[str(O8),str(O8/'runtime_fast'),str(O8/'runtime'),str(PORT),str(PORT/'source/lap-0.5.13')]
from native_graph import NativeGraph
from device_initialize import initialize
from board_runtime import decode
from frozen_input import preprocess
from frame_pipeline import FramePipeline
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 q=p.with_name(p.name+'.partial')
 with q.open('w') as f:json.dump(x,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 q.replace(p)
def savegz(p,v):
 assert not p.exists()
 with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())
def restore(box,crop,rotate):
 x,y,x2,y2=crop;h=y2-y;u1,v1,u2,v2=box
 return [v1+x,h-u2+y,v2+x,h-u1+y] if rotate else [u1+x,v1+y,u2+x,v2+y]
def main():
 p=load(ROOT/'board_protocol_v2.json');out=ROOT/'results_v2';out.mkdir(exist_ok=False);cv2.setNumThreads(1)
 state={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
  'protocol_sha256':sha(ROOT/'board_protocol_v2.json'),'scope':'Frozen192losslessPNG->actualFPGA/ARMmodel->native-coordinateboxes->actualARMByteTrackandcounters;notlivecameraorconcurrentidentity.',
  'rows':[],'scenes':[],'warmups':[],'actual_video_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
 graph=lock=None;failure=None;close_error=None
 def progress(scene,frame):write(out/'progress.json',{'status':state['status'],'PID':os.getpid(),'scene':scene,'frame0':frame,'actual_video_model_forwards':state['actual_video_model_forwards']})
 try:
  progress('before_payload_validation',None)
  for row in p['payload_files']:assert sha(ROOT/row['file'])==row['sha256']
  portsummary=load(PORT/'regression_results/summary.json');portterminal=load(PORT/'regression_results/terminal.json')
  assert portsummary['status']==portterminal['status']=='ALL90_REAL_ARM_TRACES180_COUNTER_PATHS82020_TICKS_PASS_FROZEN_TOLERANCES'
  assert portterminal['summary_sha256']==sha(PORT/'regression_results/summary.json') and not (Path('/proc')/str(portterminal['PID'])).exists()
  for row in p['tracker_files']:assert sha(PORT/row['file'])==row['sha256']
  assert sha(MODEL/'program/graph.bin')==p['graph_sha256'] and sha(MODEL/'resident_plan/resident_plan.bin')==p['resident_plan_sha256']
  assert sha(PL.bitfile_name)==p['O8_bit_sha256']
  lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  state['device_initialization']=initialize(O8)
  graph=NativeGraph(192,program=str(MODEL/'program'),plan=str(MODEL/'resident_plan/resident_plan.bin'),options=4,firmware_manifest='hardware/accepted/firmware_manifest.json')
  state['graph_memory']=graph.memory();state['model_checkpoint_sha256']=p['checkpoint_sha256'];state['PL_bitfile']=PL.bitfile_name
  inputs=load(ROOT/'board_input_manifest.json');assert len(inputs)==2654
  image=cv2.imread(str(ROOT/inputs[0]['file']));assert image.shape==(192,192,3);x=preprocess(image,192)
  for i in range(2):
   start=time.perf_counter_ns();graph.run(x);state['warmups'].append({'index':i,'tensor_to_raw_ms':(time.perf_counter_ns()-start)/1e6})
  for spec in p['videos']:
   source=[row for row in inputs if row['scene']==spec['name']]
   assert len(source)==len(range(0,spec['decode_end_exclusive'],spec['inference_stride']))
   pipelines={stride:FramePipeline(spec,p['tracker_config'],p['counter_kwargs']) for stride in spec['counter_replay_strides']}
   traces={stride:{'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]} for stride in pipelines}
   folder=out/spec['name'];folder.mkdir(exist_ok=False)
   rawarray=np.lib.format.open_memmap(folder/'all_raw.npy',mode='w+',dtype=np.float32,shape=(len(source),300,6))
   predictions=[];scene_start=time.perf_counter_ns()
   for i,row in enumerate(source):
    start=time.perf_counter_ns();file=ROOT/row['file'];image=cv2.imread(str(file));assert image.shape==(192,192,3)
    after_read=time.perf_counter_ns();x=preprocess(image,192);after_preprocess=time.perf_counter_ns()
    assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256']
    before_model=time.perf_counter_ns();raw=graph.run(x).copy();after_model=time.perf_counter_ns();state['actual_video_model_forwards']+=1
    assert raw.shape==(1,300,6) and np.isfinite(raw).all() and np.all(raw[:,:,5]==0)
    selected=decode(raw,row['oriented_crop_shape'],p['confidence'],192)
    boxes=[{'crop_oriented_xyxy':r[:4].astype(float).tolist(),'xyxy':restore(r[:4].astype(float).tolist(),spec['detection_crop_xyxy'],spec['orientation']=='clockwise90'),'confidence':float(r[4]),'class':0} for r in selected]
    after_decode=time.perf_counter_ns()
    for stride,pipeline in pipelines.items():
     if row['frame0']%stride:continue
     result=pipeline.update(row['frame0'],boxes);traces[stride]['observations'].append(result['observation'])
     for key in ['post_tracker','confirmed_only_events','handoff_events']:traces[stride][key].extend(result[key])
    after_track=time.perf_counter_ns();rawarray[i]=raw[0];predictions.append({'frame0':row['frame0'],'time_s':row['time_s'],'predictions':boxes})
    after_save=time.perf_counter_ns()
    if row['anchor']:
     expected=np.load(ROOT/'native_integer_anchors'/(row['scene']+'_f'+str(row['frame0'])+'.npz'))
     assert expected['input'].tobytes()==x.tobytes() and expected['native_integer_raw'].tobytes()==raw.tobytes(),'Heldoutvideoanchorintegerparityfailed'
    state['rows'].append({'scene':row['scene'],'frame0':row['frame0'],'PNG_read_ms':(after_read-start)/1e6,
     'preprocess_ms':(after_preprocess-after_read)/1e6,'input_hash_check_ms':(before_model-after_preprocess)/1e6,
     'tensor_to_raw_ms':(after_model-before_model)/1e6,'decode_restore_ms':(after_decode-after_model)/1e6,
     'tracker_counter_ms':(after_track-after_decode)/1e6,'raw_memorymap_and_row_save_ms':(after_save-after_track)/1e6,
     'PNG_to_counter_with_raw_save_ms':(after_save-start)/1e6,'detections':len(boxes)})
    if i%25==0:progress(spec['name'],row['frame0']);print(json.dumps({'scene':spec['name'],'source_inputs_done':i+1,'actual_forwards':state['actual_video_model_forwards']}),flush=True)
   rawarray.flush();del rawarray
   wall=(time.perf_counter_ns()-scene_start)/1e9
   savegz(folder/'raw_predictions.json.gz',predictions)
   for stride,trace in traces.items():savegz(folder/('stride'+str(stride)+'_counter_trace.json.gz'),trace)
   metrics=[]
   for stride,trace in traces.items():
    for kind in ['confirmed_only_events','handoff_events']:
     events=[e for e in trace[kind] if spec['scope_start_frame0']<=e['frame0']<spec['scope_end_exclusive']]
     metrics.append({'stride':stride,'counter':kind,'down':sum(e['direction']=='A->B' for e in events),'up':sum(e['direction']=='B->A' for e in events),'events':events})
   state['scenes'].append({'scene':spec['name'],'input_images':len(source),'PNG_to_counter_replay_wall_s_including_raw_flush':wall,'unpaced_replay_FPS':len(source)/wall,'metrics':metrics})
   write(out/'record.json',state)
  assert state['actual_video_model_forwards']==2654 and len(state['rows'])==2654
  hardware=graph.status();assert hardware['error']=='0x0'
  state.update({'status':'ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE','actual_anchor_integer_parity_bytes_exact':8,'hardware_status':hardware})
 except BaseException as e:
  failure=e;state.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc()})
 finally:
  try:
   if graph:graph.close()
  except BaseException as e:close_error=repr(e);state['status']='CLOSE_FAILED_DEVICE_STATE_UNCERTAIN'
  state['close_error']=close_error;state['memory_after']=Path('/proc/meminfo').read_text();state['PL_after']=PL.bitfile_name
  if PL.bitfile_name:state['PL_after_sha256']=sha(PL.bitfile_name)
  write(out/'record.json',state);os.sync()
  write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),'actual_video_model_forwards':state['actual_video_model_forwards'],'record_sha256':sha(out/'record.json'),'close_error':close_error})
  if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
  print(json.dumps({'status':state['status'],'actual_video_model_forwards':state['actual_video_model_forwards'],'close_error':close_error}),flush=True)
 if failure or close_error:raise SystemExit(1)
if __name__=='__main__':main()
