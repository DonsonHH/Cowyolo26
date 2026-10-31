from pathlib import Path
import os,sys,json,time,hashlib,fcntl,traceback,resource,pickle,tarfile
os.environ['XILINX_XRT']='/usr';os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import cv2,numpy as np
from pynq import PL
ROOT=Path(__file__).resolve().parent
O8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8')
VIDEO=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030')
MODEL=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_mosaic192_qual_20261030')
sys.path[:0]=[str(O8),str(O8/'runtime_fast')]
from native_graph import NativeGraph
from device_initialize import initialize
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 q=p.with_suffix(p.suffix+'.partial');q.write_text(json.dumps(x,indent=2)+'\n');q.replace(p)
def io_counters():return {k:int(v) for k,v in (line.split(':') for line in Path('/proc/self/io').read_text().splitlines())}
def snapshot():
 r=resource.getrusage(resource.RUSAGE_SELF)
 return {'cpu_ns':time.process_time_ns(),'io':io_counters(),'minor_faults':r.ru_minflt,'major_faults':r.ru_majflt}
def main():
 p=load(ROOT/'protocol.json');out=ROOT/'results';out.mkdir(exist_ok=False);cv2.setNumThreads(1)
 s={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'rows':[],'actual_O8_forwards':0,'actual_qualification_forwards':0,'actual_warmups':0,'whole_goal_complete':False}
 graph=lock=None;failure=None
 try:
  assert sha(ROOT/'board_benchmark.py')==p['runner_sha256']
  for r in p['runtime_files']:assert sha(r['file'])==r['sha256']
  assert sha(PL.bitfile_name)==p['O8_bit_sha256']
  lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  memory_before=Path('/proc/meminfo').read_text();images={};camera=Path(p['camera_root']);rows=p['source_rows'];inputs=load(VIDEO/'board_input_manifest.json')
  for r in rows:
   file=camera/r['camera_file'];assert file.stat().st_size==r['camera_bytes'];assert sha(file)==r['camera_sha256']
   imagefile=VIDEO/r['input_file'];assert sha(imagefile)==r['input_sha256'];image=cv2.imread(str(imagefile));assert image.shape==(192,192,3);images[r['frame0']]=image
  reusable=bytearray(max(r['camera_bytes'] for r in rows));s['reusable_buffer_bytes']=len(reusable)
  original=np.load(VIDEO/'results/original/all_raw.npy',mmap_mode='r');raw_frames=[];raws=[]
  for mode in ['read_only','after_actual_O8']:
   if mode=='after_actual_O8':
    s['device_initialization']=initialize(O8)
    graph=NativeGraph(192,program=str(MODEL/'program'),plan=str(MODEL/'resident_plan/resident_plan.bin'),options=4,firmware_manifest='hardware/accepted/firmware_manifest.json')
    s['graph_memory']=graph.memory()
    for anchor in [r for r in inputs if r['anchor']]:
     image=cv2.imread(str(VIDEO/anchor['file']));raw=graph.run_image(image).copy();s['actual_qualification_forwards']+=1
     with np.load(VIDEO/'native_integer_anchors'/(anchor['scene']+'_f'+str(anchor['frame0'])+'.npz')) as a:assert raw.tobytes()==a['native_integer_raw'].tobytes()
    assert s['actual_qualification_forwards']==8
    for _ in range(2):graph.run_image(images[rows[0]['frame0']]);s['actual_warmups']+=1
   for repeat in [1,2]:
    conditions=[('bytes','cold_requested'),('bytes','prewarmed'),('readinto','cold_requested'),('readinto','prewarmed')]
    source_order=rows
    if repeat==2:conditions=list(reversed(conditions));source_order=list(reversed(rows))
    for r in source_order:
     file=camera/r['camera_file'];n=r['camera_bytes'];frame=r['frame0']
     for method,cache in conditions:
      if cache=='cold_requested':
       with file.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
      else:
       warm=file.read_bytes();assert hashlib.sha256(warm).hexdigest()==r['camera_sha256'];del warm
      outer_start=time.monotonic_ns();network_ms=None;raw_sha=None
      if graph:
       t=time.monotonic_ns();raw=graph.run_image(images[frame]).copy();network_ms=(time.monotonic_ns()-t)/1e6;s['actual_O8_forwards']+=1
      before=snapshot();start=time.monotonic_ns();cpu_start=time.process_time_ns()
      if method=='bytes':payload=file.read_bytes()
      else:
       payload=memoryview(reusable)[:n]
       with file.open('rb') as f:
        offset=0
        while offset<n:
         count=f.readinto(payload[offset:]);assert count;offset+=count
        assert f.read(1)==b''
      cpu_end=time.process_time_ns();end=time.monotonic_ns();after=snapshot();outer_end=time.monotonic_ns()
      assert len(payload)==n and hashlib.sha256(payload).hexdigest()==r['camera_sha256']
      freeze_start=time.monotonic_ns();immutable=bytes(payload);freeze_end=time.monotonic_ns()
      serialization_start=time.monotonic_ns();serialized=pickle.dumps(immutable,protocol=pickle.DEFAULT_PROTOCOL);serialization_end=time.monotonic_ns()
      assert pickle.loads(serialized)==immutable
      if graph:
       assert raw.tobytes()==original[frame//5].tobytes();raw_sha=hashlib.sha256(raw.tobytes()).hexdigest()
       if frame not in raw_frames:raw_frames.append(frame);raws.append(raw[0].copy())
      s['rows'].append({'mode':mode,'repeat':repeat,'frame0':frame,'method':method,'cache_request':cache,'JPEG_bytes':n,
       'JPEG_wall_ms':(end-start)/1e6,'JPEG_process_CPU_ms':(cpu_end-cpu_start)/1e6,
       'network_ms':network_ms,'instrumented_outer_wall_ms':(outer_end-outer_start)/1e6,
       'read_bytes_delta':after['io']['read_bytes']-before['io']['read_bytes'],'rchar_delta':after['io']['rchar']-before['io']['rchar'],
       'minor_fault_delta':after['minor_faults']-before['minor_faults'],'major_fault_delta':after['major_faults']-before['major_faults'],
       'freeze_to_immutable_bytes_ms':(freeze_end-freeze_start)/1e6,'pickle_DEFAULT_PROTOCOL':pickle.DEFAULT_PROTOCOL,
       'pickle_bytes_wall_ms':(serialization_end-serialization_start)/1e6,'pickle_bytes_length':len(serialized),
       'JPEG_sha256':r['camera_sha256'],'actual_raw_sha256':raw_sha})
      del payload,immutable,serialized
     write(out/'progress.json',{'status':'RUNNING','PID':os.getpid(),'mode':mode,'repeat':repeat,'source_frame0':frame,'rows':len(s['rows']),'actual_O8_forwards':s['actual_O8_forwards']})
   write(out/('rows_'+mode+'.json'),[r for r in s['rows'] if r['mode']==mode])
  assert len(s['rows'])==256 and s['actual_O8_forwards']==128 and s['actual_qualification_forwards']==8 and s['actual_warmups']==2
  np.savez_compressed(out/'all16_actual_raw.npz',frame0=np.asarray(raw_frames),raw=np.stack(raws));assert len(raw_frames)==16
  s.update({'status':'ALL256_JPEG_READ_CASES128_REAL_O8_AFTER_READS_AND16_RAW_IMAGES_COMPLETE','hardware_status':graph.status(),'memory_before':memory_before,'current_parent_status':Path('/proc/self/status').read_text()})
  assert s['hardware_status']['error']=='0x0'
 except BaseException as e:failure=e;s.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc()})
 finally:
  close_error=None
  try:
   if graph:graph.close()
  except BaseException as e:close_error=repr(e);s['status']='CLOSE_FAILED_DEVICE_STATE_UNCERTAIN'
  s['close_error']=close_error;s['PL_after']=PL.bitfile_name;s['PL_after_sha256']=sha(PL.bitfile_name);s['memory_after']=Path('/proc/meminfo').read_text()
  write(out/'record.json',s);write(out/'terminal.json',{'status':s['status'],'PID':os.getpid(),'actual_O8_forwards':s['actual_O8_forwards'],'record_sha256':sha(out/'record.json'),'close_error':close_error})
  if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
 if failure or close_error:raise SystemExit(1)
 print(json.dumps({'status':s['status'],'rows':len(s['rows']),'actual_O8_forwards':s['actual_O8_forwards']}),flush=True)
if __name__=='__main__':main()
