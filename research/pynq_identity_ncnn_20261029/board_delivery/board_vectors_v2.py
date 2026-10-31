from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,time,traceback
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
from PIL import Image
from ncnn_encoder_v2 import Encoder,body_tensor
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):
 temp=p.with_suffix(p.suffix+'.partial');temp.write_text(json.dumps(x,indent=2)+'\n');temp.replace(p)
def main():
 p=load(ROOT/'vectors_protocol_v2.json');out=ROOT/'vectors_results_v2';out.mkdir(exist_ok=False)
 state={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
  'protocol_sha256':sha(ROOT/'vectors_protocol_v2.json'),'rows':[],'warmups':[],'model_forwards':0,'PL_actions':0,'whole_goal_complete':False}
 encoder=None;failure=None;features={};started=time.perf_counter_ns()
 try:
  built=load(ROOT/'build_v2_result.json');terminal=load(ROOT/'build_v2_terminal.json');assert terminal['success'] and not (Path('/proc')/str(terminal['PID'])).exists()
  assert sha(ROOT/'libcow_encoder_v2.so')==built['bridge_library_sha256']
  for row in p['files']:assert sha(ROOT/row['file'])==row['sha256']
  vectors=load(ROOT/'vector_manifest.json');encoder=Encoder(ROOT,threads=1)
  with np.load(ROOT/vectors[0]['file']) as a:first=a['input']
  for i in range(2):
   start=time.perf_counter_ns();encoder.run(first);state['warmups'].append({'index':i,'ms':(time.perf_counter_ns()-start)/1e6})
  for row in vectors:
   with np.load(ROOT/row['file']) as ar:x=ar['input'];reference=ar['Torch_normalized'];pc=ar['ncnn_normalized']
   start=time.perf_counter_ns();raw=encoder.run(x);elapsed=(time.perf_counter_ns()-start)/1e6;state['model_forwards']+=1
   normalized=raw/np.linalg.norm(raw);error=float(np.max(np.abs(normalized-reference)));cosine=float(normalized.astype(np.float64)@reference.astype(np.float64))
   assert error<=p['max_normalized_embedding_absolute_error'] and 1-cosine<=p['maximum_1_minus_cosine_error']
   with Image.open(ROOT/row['image_file']) as image:runtime_tensor=body_tensor(image)
   preprocessing_error=float(np.max(np.abs(runtime_tensor-x)));assert preprocessing_error<=p['Pillow_preprocessing_max_absolute_tolerance']
   features.setdefault(row['group'],[]).append(normalized)
   np.savez_compressed(out/(row['name']+'.npz'),raw=raw,normalized=normalized,runtime_body_tensor=runtime_tensor)
   report={'name':row['name'],'group':row['group'],'index':row['index'],'tensor_sha256':hashlib.sha256(x.tobytes()).hexdigest(),
    'max_normalized_embedding_difference':error,'cosine':cosine,'runtime_Pillow_tensor_max_difference':preprocessing_error,
    'model_ms':elapsed,'output_file':row['name']+'.npz','output_sha256':sha(out/(row['name']+'.npz'))}
   state['rows'].append(report)
   if len(state['rows'])%15==0:write(out/'progress.json',{'status':state['status'],'PID':os.getpid(),'completed_vectors':len(state['rows'])});print(json.dumps(report),flush=True)
  for group in features:features[group]=np.stack(features[group])
  images=load(ROOT/'image_groups.json');retrieval=[]
  # Compare all query rankings and acceptance to saved Torch features, including the explicit leakage control.
  with np.load(ROOT/'reference_features.npz') as refs:
   for gallery in ['old_gallery','new_gallery']:
    labels=p['registered_IDs'];grows=images[gallery]
    for queries in ['labelled_query','real_event_query']:
     scores={}
     for backend in ['Torch','board']:
      g=refs[gallery] if backend=='Torch' else features[gallery];q=refs[queries] if backend=='Torch' else features[queries]
      dot=q.astype(np.float64)@g.astype(np.float64).T
      scores[backend]=np.stack([np.max(dot[:,[i for i,r in enumerate(grows) if r['identity']==label]],axis=1) for label in labels],axis=1)
     a,b=scores['Torch'],scores['board'];assert np.array_equal(a.argmax(1),b.argmax(1)) and np.array_equal(a.max(1)>=p['fixed_threshold'],b.max(1)>=p['fixed_threshold'])
     retrieval.append({'gallery':gallery,'queries':queries,'all_top1_and_acceptances_exact':True,'max_similarity_difference':float(np.max(np.abs(a-b)))})
  assert len(state['rows'])==state['model_forwards']==132 and 'torch' not in sys.modules
  np.savez_compressed(out/'all_normalized_features.npz',**features)
  state.update({'status':'ALL132_ACTUAL_ARM_NCNN_VECTORS_PREPROCESS_AND_RETRIEVAL_PASS_FROZEN_GATES',
   'retrieval_checks':retrieval,'library_sha256':sha(ROOT/'libcow_encoder_v2.so'),'torch_imported':False,
   'max_normalized_embedding_difference':max(r['max_normalized_embedding_difference'] for r in state['rows']),
   'max_runtime_Pillow_tensor_difference':max(r['runtime_Pillow_tensor_max_difference'] for r in state['rows']),
   'mean_model_ms':float(np.mean([r['model_ms'] for r in state['rows']]))})
 except BaseException as e:failure=e;state.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc()})
 finally:
  if encoder:encoder.close()
  state['wall_s']=(time.perf_counter_ns()-started)/1e9;write(out/'record.json',state)
  write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),'model_forwards':state['model_forwards'],'record_sha256':sha(out/'record.json')})
  print(json.dumps({k:v for k,v in state.items() if k!='rows'}),flush=True)
 if failure:raise SystemExit(1)
if __name__=='__main__':main()
