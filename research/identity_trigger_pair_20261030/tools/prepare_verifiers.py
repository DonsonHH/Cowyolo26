from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'backend_service_20261030'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name,s):ast.parse(s);p=ROOT/'tools'/name;assert not p.exists();p.write_bytes(s.encode())
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
s=(OLD/'tools/verify_board_results.py').read_text()
s=s.replace("OUT/'final_state.json'","OUT/'final_board_state.json'").replace('ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE','ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE')
s=s.replace("and not final['proc_exists']","and final['parent_PID']==t['PID'] and final['all_runtime_hashes_match']")
s=s.replace("final['PL_bit_sha256']","final['PL_SHA256']")
anchor="galleryrows=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery']"
addition="""galleryrows=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery']
newpath=PROJECT/'identity_joint_pair_20261030/board_delivery/results/identity_qualification/all_features.npz'
assert sha(newpath)==p['models']['new']['gallery_SHA256']
with np.load(newpath)as a:newgallery=a['normalized'][:30].astype(float)
galleries={'old':gallery,'new':newgallery}
"""
s=replace(s,anchor,addition.rstrip())
s=replace(s,"known_features[job['input_tensor_sha256']]=ar['raw'].tobytes()","known_features[('old',job['input_tensor_sha256'])]=ar['raw'].tobytes()")
s=replace(s,"for run,summary in zip(p['runs'],s['cases']):","for run,summary in zip(p['runs'],s['cases']):\n gallery=galleries[run['identity_model']];assert run['identity_model']==summary['identity_model']")
s=replace(s," assert b['execution_policy']==run['policy'] and b['actual_nice']==10 and b['actual_CPU_affinity']==[0,1]"," assert b['execution_policy']==run['policy'] and b['actual_nice']==10 and b['actual_CPU_affinity']==[0,1]\n assert b['identity_model']==run['identity_model']and b['encoder_bin_sha256']==p['models'][run['identity_model']]['encoder_bin_sha256']and b['gallery_features_sha256']==p['models'][run['identity_model']]['gallery_SHA256']\n assert all(mask==[0,1]for mask in b['after_warmup_thread_affinities'].values())")
s=replace(s,"   key=job['input_tensor_sha256']","   key=(run['identity_model'],job['input_tensor_sha256'])")
s=replace(s,"  jobs+=1;job_rows.append(","  assert job['identity_model']==run['identity_model']and job['secondary_Cows_threshold_accepted']==(job['similarity']>=p['secondary_Cows_threshold'])and all(mask==[0,1]for mask in job['thread_affinities_after_job'].values())\n  jobs+=1;job_rows.append(")
s=replace(s,"{'run':run['run'],'policy':run['policy'],'repeat':run['repeat'],'event':job['event']","{'run':run['run'],'policy':run['policy'],'repeat':run['repeat'],'identity_model':run['identity_model'],'vector_file':str((bg/job['vector_file']).resolve()),'input_tensor_sha256':job['input_tensor_sha256'],'queue_wait_ms':job['queue_wait_ms'],'enqueue_to_result_ms':job['enqueue_to_result_ms'],'network_ms':job['actual_identity_network_ms'],'secondary_Cows_threshold_accepted':job['secondary_Cows_threshold_accepted'],'event':job['event']")
s=replace(s,"backgrounds.append({'run':run['run'],'policy':run['policy'],'repeat':run['repeat']","backgrounds.append({'run':run['run'],'policy':run['policy'],'repeat':run['repeat'],'identity_model':run['identity_model']")
s=s.replace('FOUR_REAL_IDLE_PARALLEL_BACKEND_PYNQ_RUNS_RAW_COUNTER_BUFFER_PHOTO_INPUT_FEATURE_AND_RETRIEVAL_VERIFIED','FOUR_ACTUAL_COUNT_TRIGGER_MODEL_PAIR_RUNS_RAW_EVENTS_CAUSAL_PHOTOS_INPUTS_MODEL_MATCHED_SCORES_VERIFIED')
s=replace(s,"'actual_background_identity_jobs':jobs,'identity_warmups':warmups","'actual_background_identity_jobs':jobs,'identity_warmups':warmups,'all_new_actual_board_forwards':rawchecks+16+jobs+warmups")
put('verify_board_results.py',s)
for name in['verify_producer_records.py','verify_CPU_records.py','independent_geometry.py']:put(name,(OLD/'tools'/name).read_text())
p=ROOT/'tools/verify_producer_records.py';s=p.read_text();s=replace(s,"  assert prod['peak_retained_frames']<=7","  assert prod['producer_affinity']==[0,1]and isinstance(prod['producer_native_TID'],int)\n  assert prod['peak_retained_frames']<=7");p.write_bytes(s.encode())
for name in['replay_tracker.py','prepare_tracker_replay.py']:
 s=(PROJECT/'identity_joint_pair_20261030/tools'/name).read_text().replace('identity_joint_pair_20261030','identity_trigger_pair_20261030').replace("ROOT/'board_delivery/results'","ROOT/'delivery/results'").replace('cow-id-pair-track','cow-trigger-track')
 put(name,s)
files=[f for f in(ROOT/'tools').glob('*.py')if f.name.startswith(('verify','replay','prepare_tracker','independent_'))]
v={'status':'TRIGGER_PAIR_LOCAL_GEOMETRY_EVENT_CPU_PRODUCER_AND_FULL_TRACKER_REPLAY_VERIFIERS_PREPARED_BEFORE_RESULTS','created_UTC':datetime.now(timezone.utc).isoformat(),'source_board_verifier_SHA256':sha(OLD/'tools/verify_board_results.py'),'files':{f.name:sha(f)for f in files},'new_model_forwards':0};(ROOT/'evidence/verification_code_binding.json').write_bytes(json.dumps(v,indent=2).encode()+bytes([10]));print(json.dumps({'verifier_files':len(files),'new_model_forwards':0}))
