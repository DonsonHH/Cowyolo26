"""FP32/QDQ quality, exact video input preparation, eight native integer anchors."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,socket,json,gzip,hashlib,time,gc
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import cv2,numpy as np,onnxruntime as ort,torch
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text())
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
 assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def savegz(p,v):
 assert not p.exists()
 with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())
def restore(box,crop,rotate):
 x,y,x2,y2=crop;h=y2-y;u1,v1,u2,v2=box
 return [v1+x,h-u2+y,v2+x,h-u1+y] if rotate else [u1+x,v1+y,u2+x,v2+y]
def main():
 assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
 cv2.setNumThreads(1);torch.set_num_threads(4)
 p=load(ROOT/'protocol/eval_v1.json');execution=load(ROOT/'protocol/execution_v1.json')
 assert execution['script_sha256']==sha(Path(__file__)) and execution['protocol_sha256']==sha(ROOT/'protocol/eval_v1.json')
 assert sha(ROOT/'input/validation_images.json')==p['validation_manifest_sha256']
 for name,digest in execution['input_and_geometry_hashes'].items():assert sha(ROOT/name)==digest
 port=PROJECT/'pynq_frontend_port_20261029';ps=load(port/'results/regression/summary.json');assert ps['trace_count']==90 and ps['observation_ticks']==82020
 portp=load(port/'regression_v1.json')
 for row in portp['files']:assert sha(port/row['file'])==row['sha256']
 sys.path[:0]=[str(port),str(ROOT/'input')]
 from frame_pipeline import FramePipeline
 from geometry import assign,reference
 from event_metrics import evaluate_events
 D=PROJECT/'pynq_mosaic192_compile_20261030/compiler_workspace';sys.path.insert(0,str(D/'runtime'))
 from board_runtime import decode
 from frozen_input import preprocess
 # All eight frozen CUDA tensors must be reproduced before any new forward.
 for key,digest in p['expected_NN_input_hashes'].items():
  with np.load(PROJECT/'factorial_lane_crop_20261029/results/roi/pixel_controls'/(key+'_NN.npz')) as archive:expected=archive['actual_input']
  pixels=np.rint(expected.transpose(1,2,0)*255).astype(np.uint8)[:,:,::-1].copy()
  observed=preprocess(pixels,p['size'])
  assert observed[0].tobytes()==expected.tobytes() and hashlib.sha256(observed.tobytes()).hexdigest()==digest
 size=p['size'];out=ROOT/'results/quality';out.mkdir(parents=True,exist_ok=False)
 sessions={};forwards={name:0 for name in ['FP32','QDQ']};allmetrics=[];boardinputs=[];anchors=[];started=time.monotonic_ns()
 for mode in ['FP32','QDQ']:
  assert sha(p[mode+'_onnx'])==p[mode+'_onnx_sha256']
  options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1;options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
  sessions[mode]=ort.InferenceSession(p[mode+'_onnx'],sess_options=options,providers=['CPUExecutionProvider'])
 def infer(mode,x):
  raw=sessions[mode].run(None,{'images':x})[0];forwards[mode]+=1
  assert raw.shape==(1,300,6) and raw.dtype==np.float32 and np.isfinite(raw).all() and np.all(raw[:,:,5]==0)
  return raw
 validation=load(ROOT/'input/validation_images.json');assert len(validation)==1571
 valrecords={m:[] for m in sessions};valraw={m:[] for m in sessions}
 priorval=gz(PROJECT/'mosaic_pair_20261030/results/evaluation_v2/mosaic050_seed26/validation_predictions.json.gz')
 priorval={r['file_name']:r for r in priorval};validation_deltas=[]
 for i,row in enumerate(validation):
  assert sha(row['image_alias'])==row['sha256'];native=cv2.imread(row['image_alias']);assert native.shape==(720,1280,3)
  image=cv2.rotate(native,cv2.ROTATE_90_CLOCKWISE);x=preprocess(image,size)
  references=[reference(a)['visible_reference_AABB'] for a in row['reference_annotations']]
  for mode in sessions:
   raw=infer(mode,x);valraw[mode].append(raw[0].copy());selected=decode(raw,image.shape,.2,size)
   predictions=[{'xyxy':restore(r[:4].astype(float).tolist(),[0,0,1280,720],True),'confidence':float(r[4]),'class':0} for r in selected]
   matches,_=assign(references,[r['xyxy'] for r in predictions])
   valrecords[mode].append({'file_name':row['file_name'],'source_sha256':row['sha256'],'reference_AABB':references,'predictions':predictions,
     'matches':[{'reference_index':a,'prediction_index':b,'IoU':score} for a,b,score in matches]})
   if mode=='FP32':
    before=priorval[row['file_name']]['predictions'];delta={'file_name':row['file_name'],'count_before':len(before),'count_ORT':len(predictions)}
    if len(before)==len(predictions):
     delta['maximum_coordinate_error']=max([max(abs(a-b) for a,b in zip(u['xyxy'],v['xyxy'])) for u,v in zip(predictions,before)]+[0.])
     delta['maximum_score_error']=max([abs(u['confidence']-v['confidence']) for u,v in zip(predictions,before)]+[0.])
    validation_deltas.append(delta)
  if i%320==0:print(json.dumps({'validation_done':i+1,'ORT_forwards':forwards}),flush=True)
 valmetrics=[]
 for mode,rows in valrecords.items():
  tp=sum(len(r['matches']) for r in rows);gt=sum(len(r['reference_AABB']) for r in rows);n=sum(len(r['predictions']) for r in rows)
  assert gt==1864
  valmetrics.append({'mode':mode,'images':1571,'references':gt,'TP':tp,'unmatched_reference':gt-tp,'unmatched_prediction':n-tp,'recall':tp/gt,'precision_vs_reference':tp/n if n else None})
  savegz(out/(mode+'_validation_predictions.json.gz'),rows)
 np.savez_compressed(out/'validation_all_raw.npz',**{mode:np.stack(values) for mode,values in valraw.items()})
 save(out/'FP32_validation_cache_comparison.json',validation_deltas);save(out/'validation_metrics.json',valmetrics)
 del valraw,valrecords;gc.collect()
 cachecomparison=[]
 for spec in p['videos']:
  assert sha(spec['path'])==spec['sha256'];cap=cv2.VideoCapture(spec['path']);assert cap.isOpened()
  x0,y0,x1,y1=spec['detection_crop_xyxy'];rotate=spec['orientation']=='clockwise90'
  folder=out/'board_inputs'/spec['name'];folder.mkdir(parents=True,exist_ok=False)
  rawrecords={mode:[] for mode in sessions};allraw={mode:[] for mode in sessions};decoded=0
  old=gz(PROJECT/'mosaic_pair_20261030/results/evaluation_v2'/p['model']/spec['name']/'raw_predictions.json.gz');old={r['frame0']:r for r in old}
  for frame in range(spec['decode_end_exclusive']):
   ok,native=cap.read();assert ok and native.shape==(spec['height'],spec['width'],3);decoded+=1
   if frame%spec['inference_stride']:continue
   crop=native[y0:y1,x0:x1].copy();image=cv2.rotate(crop,cv2.ROTATE_90_CLOCKWISE) if rotate else crop
   x=preprocess(image,size);inputsha=hashlib.sha256(x.tobytes()).hexdigest()
   anchor=frame in spec['pixel_control_frames']
   if anchor:assert inputsha==p['expected_NN_input_hashes'][spec['name']+'_f'+str(frame)+'_s192']
   padded=np.rint(x[0].transpose(1,2,0)*255).astype(np.uint8)[:,:,::-1].copy()
   assert preprocess(padded,size).tobytes()==x.tobytes()
   path=folder/('f'+str(frame).zfill(5)+'.png');assert cv2.imwrite(str(path),padded)
   boardinputs.append({'scene':spec['name'],'frame0':frame,'time_s':frame/spec['fps'],'file':path.relative_to(out).as_posix(),
      'sha256':sha(path),'input_tensor_sha256':inputsha,'oriented_crop_shape':list(image.shape),'anchor':anchor})
   outputs={}
   for mode in sessions:
    raw=infer(mode,x);outputs[mode]=raw;allraw[mode].append(raw[0].copy());selected=decode(raw,image.shape,.2,size)
    predictions=[{'crop_oriented_xyxy':r[:4].astype(float).tolist(),'xyxy':restore(r[:4].astype(float).tolist(),spec['detection_crop_xyxy'],rotate),'confidence':float(r[4]),'class':0} for r in selected]
    rawrecords[mode].append({'frame0':frame,'time_s':frame/spec['fps'],'predictions':predictions})
    if mode=='FP32':
     before=old[frame]['predictions'];d={'scene':spec['name'],'frame0':frame,'cached_count':len(before),'ORT_count':len(predictions)}
     if len(before)==len(predictions):
      d['maximum_coordinate_error']=max([max(abs(a-b) for a,b in zip(u['xyxy'],v['xyxy'])) for u,v in zip(predictions,before)]+[0.])
      d['maximum_score_error']=max([abs(u['confidence']-v['confidence']) for u,v in zip(predictions,before)]+[0.])
     cachecomparison.append(d)
   if anchor:anchors.append({'scene':spec['name'],'frame0':frame,'input':x.copy(),'FP32':outputs['FP32'].copy(),'QDQ':outputs['QDQ'].copy(),'input_tensor_sha256':inputsha})
   if frame%2500==0:print(json.dumps({'scene':spec['name'],'frame0':frame,'ORT_forwards':forwards}),flush=True)
  cap.release();assert decoded==spec['decode_end_exclusive']
  np.savez_compressed(out/(spec['name']+'_all_raw.npz'),**{mode:np.stack(values) for mode,values in allraw.items()})
  for mode,records in rawrecords.items():
   destination=out/spec['name']/mode;destination.mkdir(parents=True,exist_ok=False);savegz(destination/'raw_predictions.json.gz',records)
   byframe={r['frame0']:r['predictions'] for r in records}
   for stride in spec['counter_replay_strides']:
    pipeline=FramePipeline(spec,portp['tracker_config'],p['counter_kwargs']);trace={'observations':[],'post_tracker':[],'confirmed_only_events':[],'handoff_events':[]}
    for frame in range(0,spec['decode_end_exclusive'],stride):
     result=pipeline.update(frame,byframe[frame]);trace['observations'].append(result['observation'])
     for name in ['post_tracker','confirmed_only_events','handoff_events']:trace[name].extend(result[name])
    savegz(destination/('stride'+str(stride)+'_counter_trace.json.gz'),trace)
    for kind in ['confirmed_only_events','handoff_events']:
     events=[e for e in trace[kind] if spec['scope_start_frame0']<=e['frame0']<spec['scope_end_exclusive']]
     metric={'scene':spec['name'],'mode':mode,'stride':stride,'counter':kind,'down':sum(e['direction']=='A->B' for e in events),
      'up':sum(e['direction']=='B->A' for e in events),'events':events,'formal_event_metrics':evaluate_events(spec['reference_events'],events,2.) if spec['name']=='toros' else None}
     allmetrics.append(metric)
  print(json.dumps({'scene_complete':spec['name'],'ORT_forwards':forwards}),flush=True)
 assert len(boardinputs)==2654 and len(anchors)==8 and forwards=={'FP32':4225,'QDQ':4225}
 save(out/'board_input_manifest.json',boardinputs);save(out/'video_metrics.json',allmetrics);save(out/'FP32_video_cache_comparison.json',cachecomparison)
 # NativeGraph PC uses the complete fixed integer reference callback for dense Conv.
 sys.path.insert(0,str(D));from native_graph import NativeGraph
 q=PROJECT/'pynq_mosaic192_compile_20261030/results/qualification'
 assert sha(q/'compiled/program/graph.bin')==p['compiled_graph_sha256'] and sha(q/'resident_plan_all/resident_plan.bin')==p['resident_plan_sha256']
 graph=NativeGraph(size,pc=True,library='native_queue_linux.so',program=str(q/'compiled/program'),model_dir=str(q/'compiled/model'),plan=str(q/'resident_plan_all/resident_plan.bin'),options=4)
 native_anchors=[];anchor_folder=out/'native_integer_anchors';anchor_folder.mkdir()
 try:
  for row in anchors:
   actual=graph.run(row['input']).copy();assert actual.shape==(1,300,6) and np.isfinite(actual).all()
   path=anchor_folder/(row['scene']+'_f'+str(row['frame0'])+'.npz')
   np.savez_compressed(path,input=row['input'],native_integer_raw=actual,FP32_raw=row['FP32'],QDQ_raw=row['QDQ'])
   native_anchors.append({'scene':row['scene'],'frame0':row['frame0'],'file':path.relative_to(out).as_posix(),'sha256':sha(path),'input_tensor_sha256':row['input_tensor_sha256'],
    'native_integer_raw_sha256':hashlib.sha256(actual.tobytes()).hexdigest(),'maximum_native_vs_QDQ_box_error':float(np.max(np.abs(actual[:,:,:4]-row['QDQ'][:,:,:4]))),
    'maximum_native_vs_QDQ_score_error':float(np.max(np.abs(actual[:,:,4]-row['QDQ'][:,:,4])))})
 finally:graph.close()
 save(out/'native_integer_anchors.json',native_anchors)
 result={'status':'MOSAIC192_FP32_QDQ_FULL_VALIDATION_TWO_VIDEO_QUALITY_AND8_NATIVE_INTEGER_ANCHORS_COMPLETE',
  'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/eval_v1.json'),
  'model':p['model'],'checkpoint_sha256':p['checkpoint_sha256'],'ORT_actual_forwards':forwards,'native_integer_actual_forwards':8,
  'validation_metrics':valmetrics,'video_metrics':allmetrics,'board_input_images':len(boardinputs),'actual_NN_anchor_pixel_checks':8,
  'FP32_validation_count_difference_images':sum(r['count_before']!=r['count_ORT'] for r in validation_deltas),
  'FP32_video_count_difference_frames':sum(r['cached_count']!=r['ORT_count'] for r in cachecomparison),
  'raw_source_coordinates_saved':True,'new_training_updates':0,'calibration_changed':False,'board_actions':0,
  'new_independent_test':False,'whole_goal_complete':False,'wall_s':(time.monotonic_ns()-started)/1e9}
 save(out/'summary.json',result)
 save(ROOT/'results/artifact_manifest.json',[{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
 print(json.dumps({k:v for k,v in result.items() if k!='video_metrics'}),flush=True)
if __name__=='__main__':main()
