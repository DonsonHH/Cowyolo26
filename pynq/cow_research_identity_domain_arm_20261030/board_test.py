from pathlib import Path
import os,sys,time,json,hashlib,traceback,fcntl,socket
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['XILINX_XRT']='/usr';sys.dont_write_bytecode=True
import numpy as np
from PIL import Image
from pynq import PL

ROOT=Path(__file__).resolve().parent
LEGACY=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
sys.path.insert(0,str(LEGACY))
from ncnn_encoder_v3 import Encoder,body_tensor


def load(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):
 temporary=path.with_suffix(path.suffix+'.partial');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.replace(path)


def main():
 plan=load(ROOT/'run_protocol.json');out=ROOT/'results';out.mkdir(exist_ok=False)
 state={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'protocol_sha256':sha(ROOT/'run_protocol.json'),'model_forwards':0,'warmups':[],'rows':[],
        'new_training_updates':0,'new_PL_forwards':0,'PL_programming':False,'whole_goal_complete':False}
 encoder=lock=None;failure=None
 try:
  assert sha(PL.bitfile_name)==plan['O8_bit_sha256']
  assert sha(LEGACY/'encoder.ncnn.bin')==plan['default_old_encoder_bin_sha256']
  assert sha(LEGACY/'libcow_encoder_v2.so')==plan['library_sha256']and sha(LEGACY/'ncnn_encoder_v3.py')==plan['body_module_sha256']
  for row in plan['payload_files']:assert sha(ROOT/row['file'])==row['sha256']
  lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  # This task uses the CPU only; holding the shared job lock keeps the audit context stable.
  link=ROOT/'libcow_encoder_v2.so';assert not link.exists();link.symlink_to(LEGACY/'libcow_encoder_v2.so');assert sha(link)==plan['library_sha256']
  with np.load(ROOT/'reference_features.npz')as archive:reference={key:archive[key].copy()for key in archive.files}
  inputs=[];preprocess=[]
  for row in plan['images']:
   path=Path(row['existing_board_image'])if row.get('existing_board_image')else ROOT/row['payload_image']
   assert sha(path)==row['image_SHA256'];start=time.monotonic_ns()
   with Image.open(path)as image:image.load();x=body_tensor(image)
   elapsed=(time.monotonic_ns()-start)/1e6;digest=hashlib.sha256(x.tobytes()).hexdigest();assert digest==row['input_tensor_sha256']
   inputs.append(x);preprocess.append({'index':row['test_index'],'input_tensor_sha256':digest,'JPEG_decode_and_preprocess_ms':elapsed})
  write(out/'preprocessing_gate.json',{'status':'ALL97_PHOTO_INPUT_HASHES_EXACT_BEFORE_NATIVE_CREATE_OR_FORWARD','rows':preprocess,'model_forwards':0})
  encoder=Encoder(ROOT,threads=1)
  for index in range(2):
   start=time.monotonic_ns();encoder.run(inputs[0]);state['warmups'].append({'index':index,'ms':(time.monotonic_ns()-start)/1e6})
  raws=[];normalized=[]
  anchors=out/'input_anchors';anchors.mkdir()
  for row,x in zip(plan['images'],inputs):
   index=row['test_index'];start=time.monotonic_ns();raw=encoder.run(x);elapsed=(time.monotonic_ns()-start)/1e6;state['model_forwards']+=1
   feature=raw/np.linalg.norm(raw);error=float(np.max(np.abs(feature-reference['Torch_normalized'][index])));cosine=1-float(feature.astype(float)@reference['Torch_normalized'][index].astype(float))
   assert error<=plan['normalized_feature_max_absolute_error']and cosine<=plan['max_1_minus_cosine_error']
   record={'test_index':index,'source_global630_index':row['source_global630_index'],'input_tensor_sha256':hashlib.sha256(x.tobytes()).hexdigest(),
           'actual_ARM_raw_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),'normalized_Torch_error':error,'one_minus_cosine':cosine,'network_ms':elapsed}
   state['rows'].append(record);raws.append(raw);normalized.append(feature)
   if index in plan['input_anchor_test_indices']:np.savez_compressed(anchors/('test'+str(index)+'.npz'),input=x,raw=raw,normalized=feature)
   if len(raws)%15==0:write(out/'progress.json',{'status':'RUNNING','PID':os.getpid(),'completed_actual_ARM_forwards':len(raws)});print(json.dumps(record),flush=True)
  raws=np.stack(raws);normalized=np.stack(normalized);np.savez_compressed(out/'all_actual_features.npz',raw=raws,normalized=normalized)
  gi=[row['test_index']for row in plan['images']if row['dataset']=='MultiCam2023'and row['purpose']=='gallery']
  qi=[row['test_index']for row in plan['images']if row['dataset']=='MultiCam2023'and row['purpose']!='gallery'];labels=sorted({plan['images'][index]['identity']for index in gi})
  scores={}
  for name,values in[('Torch',reference['Torch_normalized']),('ARM',normalized)]:
   dot=values[qi].astype(float)@values[gi].astype(float).T;scores[name]=np.stack([dot[:,[j for j,index in enumerate(gi)if plan['images'][index]['identity']==identity]].max(axis=1)for identity in labels],axis=1)
  retrieval=[]
  for name,tau in[('original_MultiCam',plan['original_MultiCam_threshold']),('new_Cows_calibrated',plan['new_Cows_threshold'])]:
   for pos,index in enumerate(qi):
    a,b=int(np.argmax(scores['Torch'][pos])),int(np.argmax(scores['ARM'][pos]));assert a==b and bool(scores['Torch'][pos,a]>=tau)==bool(scores['ARM'][pos,b]>=tau)
    retrieval.append({'policy':name,'test_index':index,'predicted_ID':labels[b],'accepted':bool(scores['ARM'][pos,b]>=tau),
                      'reference_predicted_ID':labels[a],'reference_accepted':bool(scores['Torch'][pos,a]>=tau),'maximum_cosine_difference':float(np.max(np.abs(scores['Torch'][pos]-scores['ARM'][pos])))})
  write(out/'retrieval_parity.json',retrieval)
  assert len(state['rows'])==state['model_forwards']==97 and len(retrieval)==120 and'torch'not in sys.modules
  state.update({'status':'ALL97_NEW_ENCODER_ARM_VECTORS_INPUT_HASHES_AND120_RETENTION_DECISIONS_PASS',
                'mean_network_ms':float(np.mean([row['network_ms']for row in state['rows']])),
                'P95_network_ms':float(np.quantile([row['network_ms']for row in state['rows']],.95)),
                'maximum_normalized_feature_error':max(row['normalized_Torch_error']for row in state['rows']),
                'default_old_encoder_bin_unchanged':sha(LEGACY/'encoder.ncnn.bin')==plan['default_old_encoder_bin_sha256'],
                'Torch_imported':False,'current_PL_bitfile':PL.bitfile_name,'current_PL_sha256':sha(PL.bitfile_name)})
 except BaseException as error:
  failure=error;state.update({'status':'FAILED','error':repr(error),'traceback':traceback.format_exc()})
 finally:
  if encoder:encoder.close()
  if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
  write(out/'record.json',state);os.sync();write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),'model_forwards':state['model_forwards'],'record_sha256':sha(out/'record.json')})
  print(json.dumps({key:value for key,value in state.items()if key!='rows'}),flush=True)
 if failure:raise SystemExit(1)


if __name__=='__main__':main()
