"""Bind serial evidence to independent local source pixels, tensors and scores."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,hashlib,tarfile,math,sys,importlib.util
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mod(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
transfer=load(ROOT/'evidence/numeric_UART_transfer.json');archive=ROOT/'numeric_recovery_UART.tar.gz'
assert transfer['status']=='UART_NUMERIC_ARCHIVE_COMPLETE_HASH_VERIFIED' and sha(archive)==transfer['sha256'] and archive.stat().st_size==transfer['bytes']
out=ROOT/'numeric_recovery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==6
 for member in members:
  name=PurePosixPath(member.name);assert member.isfile() and not name.is_absolute() and '..' not in name.parts
  f=out.joinpath(*name.parts).resolve();assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(member).read())
for r in load(out/'numeric_recovery_manifest.json'):assert sha(out/r['file'])==r['sha256'] and (out/r['file']).stat().st_size==r['bytes']
assert sha(out/'audit_board_files_recovery.py')==sha(ROOT/'tools/audit_board_files_recovery.py')
audit=load(out/'board_file_audit.json');meta=ROOT/'metadata_recovery';p=load(meta/'run_protocol.json');v=load(ROOT/'results/UART_metadata_audit.json')
assert audit['status']=='ON_BOARD_ALL178_MANIFEST_FILES1466_RAW39_PHOTO_INPUT_FEATURE_AND_RETRIEVAL_RECOMPUTED'
assert audit['original_manifest_sha256']==sha(meta/'result_manifest.json') and audit['source_record_sha256']==sha(meta/'results/record.json')
assert audit['original_files_verified']==178 and audit['all_actual_raws_byte_exact']==1466 and audit['photos_verified']==39
oldraw=np.load(PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/all_raw.npy',mmap_mode='r');raw_bindings=load(out/'recovered_raw_bindings.json');rawkeys=set()
for row in raw_bindings:
 key=(row['run'],row['frame0']);assert key not in rawkeys;rawkeys.add(key)
 expected=hashlib.sha256(oldraw[row['frame0']//5].tobytes()).hexdigest();assert row['actual_raw_sha256']==row['prior_raw_sha256']==expected
assert len(rawkeys)==1466
body=mod('recovery_frozen_body_transform',PROJECT/'pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py')
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz') as ar:gallery=ar['new_gallery'].astype(float)
grows=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery'];labels=p['registered_IDs'];bindings=load(out/'recovered_photo_bindings.json')
dest=ROOT/'reconstructed_photos';dest.mkdir(exist_ok=False);jobrows=[];source_records=[];frozen_inputs=[];file_hash_same=0
with np.load(out/'recovered_actual_features.npz') as features:
 assert features['raw'].shape==features['normalized'].shape==(39,576) and features['scores'].shape==(39,6)
 for i,r in enumerate(bindings):
  folder=meta/'results'/r['run']/'background';original=load(folder/'record.json')['jobs'][r['index']]
  assert original['event']==r['event'] and original['source_frame0']==r['source_frame0'] and original['photo_sha256']==r['photo_sha256'] and original['raw_feature_sha256']==r['raw_feature_sha256']
  camera=PROJECT/'pynq_periodic_joint_20261030/camera_delivery/highres'/('f'+str(r['source_frame0']).zfill(5)+'.jpg');assert sha(camera)==original['source_JPEG_sha256']
  x,y,z,w=original['native_selected_tracker_box'];crop=[max(0,math.floor(x-870)),max(0,math.floor(y)),min(1050,math.ceil(z-870)),min(1440,math.ceil(w))];assert crop==r['crop']
  with Image.open(camera) as image:image.load();photo=image.convert('RGB').crop(crop).transpose(Image.Transpose.ROTATE_270)
  assert list(photo.size)==r['photo_WH'] and hashlib.sha256(photo.tobytes()).hexdigest()==r['photo_decoded_RGB_sha256']
  file=dest/('query'+str(i).zfill(3)+'_'+r['run']+'_f'+str(r['source_frame0'])+'.png');photo.save(file,compress_level=0)
  same=sha(file)==r['photo_sha256'];file_hash_same+=same
  tensor=body.body_tensor(photo);assert hashlib.sha256(tensor.tobytes()).hexdigest()==original['input_tensor_sha256']==r['input_tensor_sha256']
  raw=features['raw'][i];actual_normal=features['normalized'][i];assert hashlib.sha256(raw.tobytes()).hexdigest()==r['raw_feature_sha256']
  expected_normal=raw/np.linalg.norm(raw);assert expected_normal.tobytes()==actual_normal.tobytes()
  dots=actual_normal.astype(float)@gallery.T;scores=np.asarray([max(dots[k] for k,g in enumerate(grows) if g['identity']==label) for label in labels]);winner=int(np.argmax(scores))
  assert np.max(np.abs(scores-features['scores'][i]))<1e-12 and labels[winner]==r['predicted_id']==original['predicted_id']
  assert float(scores[winner])==r['similarity']==original['similarity'] and bool(scores[winner]>=p['fixed_identity_threshold'])==r['accepted']==original['accepted']
  f=dest/('query'+str(i).zfill(3)+'_reconstructed_input_and_actual_features.npz');np.savez_compressed(f,input=tensor,raw=raw,normalized=actual_normal,scores=features['scores'][i]);frozen_inputs.append({'file':str(f.resolve()),'sha256':sha(f)})
  jobrows.append({'run':r['run'],'policy':next(s['policy'] for s in p['runs'] if s['run']==r['run']),'repeat':next(s['repeat'] for s in p['runs'] if s['run']==r['run']),
   'event':r['event'],'source_frame0':r['source_frame0'],'selected_age_frames':original['event_source_frame0']-r['source_frame0'],'candidate_count':len(original['selection']['candidates']),
   'predicted_id':r['predicted_id'],'similarity':r['similarity'],'accepted':r['accepted'],'photo_file':str(file.resolve()),'photo_sha256':sha(file),'used_geometry':original['selection']['used_candidate'],
   'original_board_photo_SHA256':r['photo_sha256'],'reconstructed_photo_pixels_exact_to_onboard_original':True,'original_board_PNG_file_byte_identical':same,
   'vector_file':str(f.resolve()),'vector_sha256':sha(f),'original_board_vector_file_SHA256':original['vector_sha256']})
  source_records.append({'run':r['run'],'photo_source':str(camera.resolve()),'original_PNG_sha256':r['photo_sha256'],'reconstructed_PNG_sha256':sha(file),
   'decoded_RGB_sha256':r['photo_decoded_RGB_sha256'],'input_tensor_SHA256':r['input_tensor_sha256'],'raw_feature_SHA256':r['raw_feature_sha256']})
assert len(jobrows)==39
result={'status':'SERIAL_NUMERIC_PROOFS_AND_LOCAL39_PHOTO_PIXELS_INPUTS_ACTUAL_FEATURES_SCORES_RECONSTRUCTED_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'original_board_manifest_files_read_and_hash_verified_on_board':178,'actual_O8_raw_cases_verified_on_board_and_hash_bound_locally':1466,
 'counter_observation_ticks':v['counter_observation_ticks'],'counter_paths':8,'actual_background_identity_jobs':39,'photos_pixels_verified':39,
 'reconstructed_PNG_files_byte_identical_to_board_PNGs':file_hash_same,'input_tensors_byte_exact':39,'raw_feature_bytes_bound_to_original_job_hashes':39,'retrieval_decisions_recomputed':39,
 'source_records':source_records,'reconstructed_input_archives':frozen_inputs,'raw_arrays_locally_downloaded':False,'original_full_archive_locally_downloaded':False,
 'onboard_file_audit_not_new_model_forward':True,'new_model_forwards':0,'whole_goal_complete':False}
for name,value in [('recovery_independent_verification.json',result),('actual_job_rows.json',jobrows)]:
 f=ROOT/'results'/name;assert not f.exists();f.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['source_records','reconstructed_input_archives']}))
