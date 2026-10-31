"""Each count-triggered job loads its same-frame high-resolution replay image."""
from pathlib import Path
import os,sys,time,json,hashlib,math,traceback
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1'
import numpy as np
from PIL import Image
ENCODER=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
sys.path.insert(0,str(ENCODER))
from ncnn_encoder_v3 import Encoder,body_tensor
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 t=p.with_suffix(p.suffix+'.partial');t.write_text(json.dumps(x,indent=2)+'\n');t.replace(p)
def worker(requests,ready,destination,root,protocol):
 out=Path(destination);out.mkdir(exist_ok=False);root=Path(root);os.nice(protocol['backend_nice_increment'])
 encoder=None;state={'status':'RUNNING','PID':os.getpid(),'jobs':[],'model_forwards':0,'warmups':[],'PL_actions':0,'whole_goal_complete':False,'execution_policy':'idle_gate' if protocol.get('worker_idle_gated') else 'direct_background','PNG_compress_level':0}
 try:
  encoder=Encoder(ENCODER,threads=1)
  with np.load(ENCODER/'vectors_results_v3/all_normalized_features.npz') as a:gallery=a['new_gallery'].astype(np.float64)
  groups=json.loads((ENCODER/'image_groups.json').read_text());labels=protocol['registered_IDs'];grows=groups['new_gallery']
  with np.load(ENCODER/'vectors/old_gallery_000.npz') as a:x=a['input']
  t=time.monotonic_ns();encoder.run(x);state['warmups'].append({'ms':(time.monotonic_ns()-t)/1e6})
  ready.put({'status':'READY','PID':os.getpid()})
  while True:
   job=requests.get()
   if job is None:break
   start=time.monotonic_ns();cpu_start=time.process_time_ns();frame=job['source_frame0'];file=root/'camera/highres'/('f'+str(frame).zfill(5)+'.jpg')
   with Image.open(file) as im:
    im.load();image=im.convert('RGB');assert image.size==(1050,1440)
   decoded=time.monotonic_ns();box=job['box_native_xyxy'];left,top,right,bottom=box
   crop=[max(0,math.floor(left-870)),max(0,math.floor(top)),min(1050,math.ceil(right-870)),min(1440,math.ceil(bottom))]
   assert crop[0]<crop[2] and crop[1]<crop[3]
   photo=image.crop(crop).transpose(getattr(Image,'Transpose',Image).ROTATE_270)
   name='job'+str(len(state['jobs'])).zfill(3)+'_f'+str(frame)+'_tid'+str(job['event']['track_id'])
   photo_file=out/(name+'.png');photo.save(photo_file,compress_level=0);captured=time.monotonic_ns()
   x=body_tensor(photo);preprocessed=time.monotonic_ns();network_cpu_start=time.process_time_ns();raw=encoder.run(x);state['model_forwards']+=1;inferred=time.monotonic_ns();network_cpu_end=time.process_time_ns()
   feature=raw/np.linalg.norm(raw);dots=feature.astype(np.float64)@gallery.T
   scores=np.asarray([max(dots[i] for i,r in enumerate(grows) if r['identity']==label) for label in labels]);winner=int(np.argmax(scores))
   result={'source_frame0':frame,'event':job['event'],'simulated_RFID_read':False,'predicted_id':labels[winner],
    'similarity':float(scores[winner]),'accepted':bool(scores[winner]>=protocol['fixed_identity_threshold']),
    'identity_reference_available':False,'retrieval_scores_by_registered_ID':{label:float(value) for label,value in zip(labels,scores)},
    'release_monotonic_ns':job['release_monotonic_ns'],'enqueued_monotonic_ns':job['enqueued_monotonic_ns'],'started_monotonic_ns':start,
    'inference_finished_monotonic_ns':inferred,'queue_wait_ms':(start-job['enqueued_monotonic_ns'])/1e6,
    'highres_JPEG_read_ms':(decoded-start)/1e6,'runtime_native_crop_and_photo_save_ms':(captured-decoded)/1e6,
    'Pillow_preprocess_ms':(preprocessed-captured)/1e6,'actual_identity_network_ms':(inferred-preprocessed)/1e6,'identity_network_process_CPU_ms':(network_cpu_end-network_cpu_start)/1e6,
    'native_source_crop_xyxy':crop,'native_current_tracker_box':box,'source_camera_file':str(file),
    'photo_file':photo_file.name,'photo_sha256':sha(photo_file),'photo_size_WH':list(photo.size),
    'input_tensor_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'raw_feature_sha256':hashlib.sha256(raw.tobytes()).hexdigest()}
   vector=out/(name+'.npz');np.savez_compressed(vector,input=x,raw=raw,normalized=feature,scores=scores)
   result['vector_file']=vector.name;result['vector_sha256']=sha(vector)
   result['completed_monotonic_ns']=time.monotonic_ns();result['worker_process_CPU_ms']=(time.process_time_ns()-cpu_start)/1e6;result['enqueue_to_result_ms']=(result['completed_monotonic_ns']-job['enqueued_monotonic_ns'])/1e6
   state['jobs'].append(result);write(out/(name+'.json'),result)
  assert 'torch' not in sys.modules
  state.update({'status':'ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE','torch_imported':False})
 except BaseException as e:
  state.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc()})
  try:ready.put_nowait({'status':'FAILED','error':repr(e)})
  except Exception:pass
 finally:
  if encoder:encoder.close()
  write(out/'record.json',state);write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),'model_forwards':state['model_forwards'],'record_sha256':sha(out/'record.json')})
