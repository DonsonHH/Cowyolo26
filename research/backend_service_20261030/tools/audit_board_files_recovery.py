"""Separate on-board file audit after Ethernet loss. No model/device forwards."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,gzip,hashlib,math,tarfile,traceback
os.environ['OMP_NUM_THREADS']='1';os.environ['OPENBLAS_NUM_THREADS']='1';sys.dont_write_bytecode=True
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parent
TASK=Path('/home/xilinx/jupyter_notebooks/cow_research_backend_service_20261030')
VIDEO=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_video_20261030')
ENCODER=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
sys.path.insert(0,str(ENCODER))
from ncnn_encoder_v3 import body_tensor
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n')
state={'status':'RUNNING','PID':os.getpid(),'new_model_forwards':0,'PL_actions':0,'whole_goal_complete':False}
try:
 p=load(TASK/'run_protocol.json');s=load(TASK/'results/record.json');t=load(TASK/'results/terminal.json');manifest=load(TASK/'result_manifest.json')
 assert s['status']==t['status']=='ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE'
 assert not (Path('/proc')/str(t['PID'])).exists() and sha(TASK/'results/record.json')==t['record_sha256']
 for row in manifest:assert sha(TASK/row['file'])==row['sha256'] and (TASK/row['file']).stat().st_size==row['bytes']
 old=np.load(VIDEO/'results/original/all_raw.npy',mmap_mode='r')
 with np.load(ENCODER/'vectors_results_v3/all_normalized_features.npz') as ar:gallery=ar['new_gallery'].astype(np.float64)
 grows=load(ENCODER/'image_groups.json')['new_gallery'];labels=p['registered_IDs']
 jobs=[];raws=[];normalized=[];scores_all=[];all_raw_frames=[];all_raw_outputs=[];camera=Path(p['camera_root']);raw_checks=0
 for run in p['runs']:
  folder=TASK/'results'/run['run'];bg=load(folder/'background/record.json');bt=load(folder/'background/terminal.json')
  assert sha(folder/'background/record.json')==bt['record_sha256'] and not (Path('/proc')/str(bt['PID'])).exists()
  with np.load(folder/'actual_raw.npz') as ar:
   for frame,raw in zip(ar['frame0'],ar['raw']):
    assert raw.tobytes()==old[int(frame)//5].tobytes();raw_checks+=1
    all_raw_frames.append({'run':run['run'],'frame0':int(frame),'actual_raw_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),'prior_raw_sha256':hashlib.sha256(old[int(frame)//5].tobytes()).hexdigest()})
  for index,job in enumerate(bg['jobs']):
   f=camera/'highres'/('f'+str(job['source_frame0']).zfill(5)+'.jpg');assert sha(f)==job['source_JPEG_sha256']
   x,y,z,w=job['native_selected_tracker_box'];crop=[max(0,math.floor(x-870)),max(0,math.floor(y)),min(1050,math.ceil(z-870)),min(1440,math.ceil(w))]
   assert crop==job['native_source_crop_xyxy']
   with Image.open(f) as image:image.load();expected=image.convert('RGB').crop(crop).transpose(getattr(Image,'Transpose',Image).ROTATE_270)
   photo=folder/'background'/job['photo_file'];assert sha(photo)==job['photo_sha256']
   with Image.open(photo) as image:image.load();actual=image.convert('RGB');assert expected.size==actual.size and expected.tobytes()==actual.tobytes()
   tensor=body_tensor(expected);assert hashlib.sha256(tensor.tobytes()).hexdigest()==job['input_tensor_sha256']
   vf=folder/'background'/job['vector_file'];assert sha(vf)==job['vector_sha256']
   with np.load(vf) as ar:
    assert tensor.tobytes()==ar['input'].tobytes() and hashlib.sha256(ar['raw'].tobytes()).hexdigest()==job['raw_feature_sha256']
    feature=ar['raw']/np.linalg.norm(ar['raw']);assert feature.tobytes()==ar['normalized'].tobytes()
    dots=ar['normalized'].astype(np.float64)@gallery.T
    scores=np.asarray([max(dots[i] for i,g in enumerate(grows) if g['identity']==label) for label in labels]);winner=int(np.argmax(scores))
    assert scores.tobytes()==ar['scores'].tobytes() and labels[winner]==job['predicted_id'] and float(scores[winner])==job['similarity'] and bool(scores[winner]>=p['fixed_identity_threshold'])==job['accepted']
    raws.append(ar['raw'].copy());normalized.append(ar['normalized'].copy());scores_all.append(scores.copy())
   jobs.append({'run':run['run'],'index':index,'source_frame0':job['source_frame0'],'event':job['event'],'photo_file':str(photo),'photo_sha256':sha(photo),
    'photo_decoded_RGB_sha256':hashlib.sha256(actual.tobytes()).hexdigest(),'photo_WH':list(actual.size),'crop':crop,'input_tensor_sha256':job['input_tensor_sha256'],
    'raw_feature_sha256':job['raw_feature_sha256'],'original_vector_sha256':sha(vf),'predicted_id':job['predicted_id'],'similarity':job['similarity'],'accepted':job['accepted']})
 assert raw_checks==1466 and len(jobs)==39
 features=ROOT/'recovered_actual_features.npz';assert not features.exists();np.savez_compressed(features,raw=np.stack(raws),normalized=np.stack(normalized),scores=np.stack(scores_all))
 jfile=ROOT/'recovered_photo_bindings.json';write(jfile,jobs)
 rfile=ROOT/'recovered_raw_bindings.json';write(rfile,all_raw_frames)
 report={'status':'ON_BOARD_ALL178_MANIFEST_FILES1466_RAW39_PHOTO_INPUT_FEATURE_AND_RETRIEVAL_RECOMPUTED','PID':os.getpid(),
  'source_record_sha256':sha(TASK/'results/record.json'),'original_manifest_sha256':sha(TASK/'result_manifest.json'),'original_files_verified':len(manifest),'all_actual_raws_byte_exact':raw_checks,
  'photos_verified':len(jobs),'photo_pixels_reconstructed_equal':True,'all_input_tensors_byte_exact':True,'all_raw_features_and_gallery_scores_verified':True,
  'new_model_forwards':0,'PL_actions':0,'complete_original_archive_downloaded':False,'whole_goal_complete':False}
 rep=ROOT/'board_file_audit.json';write(rep,report)
 files=[features,jfile,rfile,rep,Path(__file__)];mf=ROOT/'numeric_recovery_manifest.json';write(mf,[{'file':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in files])
 a=ROOT/'numeric_recovery.tar.gz';assert not a.exists()
 with tarfile.open(a,'w:gz') as tar:
  for f in [*files,mf]:tar.add(f,arcname=f.name,recursive=False)
 transfer={'path':str(a),'bytes':a.stat().st_size,'sha256':sha(a),'members':6};write(ROOT/'numeric_transfer.json',transfer)
 state.update({'status':'NUMERIC_RECOVERY_AUDIT_COMPLETE','audit':report,'transfer':transfer})
except BaseException as e:state.update({'status':'FAILED','error':repr(e),'traceback':traceback.format_exc()})
finally:write(ROOT/'numeric_audit_terminal.json',state)
print(json.dumps(state),flush=True)
if state['status']!='NUMERIC_RECOVERY_AUDIT_COMPLETE':raise SystemExit(1)
