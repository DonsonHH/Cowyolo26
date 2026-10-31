from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,tarfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'cpu_partition_free_20261030'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(name,text):
 ast.parse(text)if name.endswith('.py')else None
 p=ROOT/'tools'/name;assert not p.exists();p.write_bytes(text.encode());return p

assert load(ROOT/'results/cpu_reference_verification.json')['images']==40
plan=load(OLD/'protocol/run_v1.json')
worker=(OLD/'tools/background_fixed_worker.py').read_text()
worker=worker.replace('encoder=Encoder(ENCODER,threads=1)',"model=protocol['models'][protocol['identity_model']];encoder=Encoder(Path(model['encoder_directory']),threads=1);state['identity_model']=protocol['identity_model'];state['encoder_bin_sha256']=sha(Path(model['encoder_directory'])/'encoder.ncnn.bin');assert state['encoder_bin_sha256']==model['encoder_bin_sha256']")
worker=worker.replace("with np.load(ENCODER/'vectors_results_v3/all_normalized_features.npz') as a:gallery=a['new_gallery'].astype(np.float64)","gallery_path=Path(model['gallery_features_file']);assert gallery_path.is_file()\n  with np.load(gallery_path)as a:gallery=a[model['gallery_array_key']][:30].astype(np.float64)")
worker=worker.replace("expected=protocol['fixed_jobs'][job['fixed_job_index']]['expected_prior_actual']","expected=protocol['fixed_jobs'][job['fixed_job_index']]['expected_prior_actual']if protocol['identity_model']=='old'else json.loads((Path(protocol['task_root'])/'results/identity_qualification/expected_queries.json').read_text())[job['fixed_job_index']]")
worker=worker.replace("for key in ['photo_sha256','input_tensor_sha256','raw_feature_sha256']:assert result[key]==expected[key],('same_fixed_job',job['fixed_job_index'],key)","for key in ['photo_sha256','input_tensor_sha256']:assert result[key]==protocol['fixed_jobs'][job['fixed_job_index']]['expected_prior_actual'][key],('same_fixed_job',job['fixed_job_index'],key)\n   assert result['raw_feature_sha256']==expected['raw_feature_sha256']")
worker=worker.replace("result['completed_monotonic_ns']=time.monotonic_ns();", "result['identity_model']=protocol['identity_model'];result['secondary_Cows_threshold_accepted']=bool(result['similarity']>=protocol['secondary_Cows_threshold']);result['gallery_features_sha256']=sha(gallery_path)\n   result['completed_monotonic_ns']=time.monotonic_ns();")
put('background_fixed_worker.py',worker)
main=(OLD/'tools/board_partition_repeats.py').read_text().replace('from process_cpu import snapshot','from process_cpu import snapshot\nfrom identity_qualification import qualify')
needle='        state["initialization"] = initialize(O8)';assert main.count(needle)==1;main=main.replace(needle,'        state["identity_qualification"] = qualify(ROOT, protocol)\n'+needle)
main=main.replace('"CPU_assignment_policy": run["policy"]}', '"CPU_assignment_policy": run["policy"], "identity_model": run["identity_model"]}')
main=main.replace('ALL4_FIXED10_JOB_CPU_AFFINITY_O8_ARM_REPEATS_COMPLETE','ALL4_OLD_NEW_NEW_OLD_IDENTITY_FIXED10_O8_ARM_REPEATS_COMPLETE');put('board_pair_repeats.py',main)
for name in['fixed_arrivals.py','process_cpu.py']:put(name,(OLD/'tools'/name).read_text())
collect=(OLD/'tools/collect_results.py').read_text().replace('ALL4_FIXED10_JOB_CPU_AFFINITY_O8_ARM_REPEATS_COMPLETE','ALL4_OLD_NEW_NEW_OLD_IDENTITY_FIXED10_O8_ARM_REPEATS_COMPLETE').replace('cpu_partition_delivery_v1.tar.xz','identity_pair_delivery_v1.tar.xz').replace('FULL_ORIGINAL_FIXED_JOB_ARCHIVE_COMPLETE','FULL_ORIGINAL_IDENTITY_PAIR_ARCHIVE_COMPLETE')
collect=collect.replace('import os, json, hashlib, tarfile, traceback, lzma','import os, json, hashlib, tarfile, traceback, lzma, socket, fcntl')
collect=collect.replace('    children = []','    assert state["identity_qualification"]["measured_forwards"]==40 and state["identity_qualification"]["warmup_forwards"]==1\n    for row in protocol["runtime_files"]:assert sha(Path(row["file"]))==row["sha256"]\n    lock=Path("/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock").open("r");fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()\n    for port in[22,9090]:connection=socket.create_connection(("127.0.0.1",port),timeout=2);connection.close()\n    children = []')
collect=collect.replace('"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "memory": Path("/proc/meminfo").read_text()', '"boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(), "memory": Path("/proc/meminfo").read_text(), "runtime_hashes_match":True,"shared_lock_available":True,"local_services":{"22":True,"9090":True},"eth0_carrier":Path("/sys/class/net/eth0/carrier").read_text().strip()')
put('collect_results.py',collect)
oldroot='/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029';newroot='/home/xilinx/jupyter_notebooks/cow_research_identity_domain_arm_20261030';remote='/home/xilinx/jupyter_notebooks/cow_research_identity_joint_pair_20261030'
plan.update({'status':'FROZEN_PAIRED_OLD_NEW_NEW_OLD_ENCODER_BEFORE_FIRST_NEW_BOARD_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),'task_root':remote,'identity_reference_images':load(ROOT/'protocol/cpu_reference_v1.json')['images'],
 'models':{'old':{'encoder_directory':oldroot,'encoder_bin_sha256':'8a7ac92f1d25259412c86a9f5e4f66a3c74db71128410fc03383a8f935e6815b','gallery_features_file':oldroot+'/vectors_results_v3/all_normalized_features.npz','gallery_array_key':'new_gallery'},
 'new':{'encoder_directory':newroot,'encoder_bin_sha256':'2a587d0fe293d244eb5632feb0e3665cf6091243198612b59363a6a7bb173252','gallery_features_file':remote+'/results/identity_qualification/all_features.npz','gallery_array_key':'normalized'}},
 'secondary_Cows_threshold':.8707458695890389,'runs':[{'run':name,'identity_model':model,'policy':'shared','background_affinity':[0,1],'repeat':repeat}for name,model,repeat in [('r1_old','old',1),('r1_new','new',1),('r2_new','new',2),('r2_old','old',2)]],
 'plan_sha256':sha(ROOT/'计划与验收.md'),'cpu_reference_protocol_sha256':sha(ROOT/'protocol/cpu_reference_v1.json'),'prior_control_protocol_sha256':sha(OLD/'protocol/run_v1.json'),
 'new_training_updates':0,'new_independent_test':False,'default_policy_changed':False,'future20_ID_pixels_opened':False,'whole_goal_complete':False})
plan['runtime_files'] += [{'file':newroot+'/'+name,'sha256':sha(PROJECT/'identity_domain_arm_20261030/payload'/name)}for name in['encoder.ncnn.param','encoder.ncnn.bin']]
plan['runtime_files'].append({'file':newroot+'/libcow_encoder_v2.so','sha256':'61519ebcc96c1ca396db3b9e6da96cb2c4ef1303b94a974ed491459e5c4e0731'})
for obsolete in['background_encoder','first_stage_counts_seen','first_stage_O8_timed_forwards_seen','first_stage_record_sha256','first_stage_protocol_sha256']:plan.pop(obsolete,None)
payload=ROOT/'payload';payload.mkdir(exist_ok=False)
names=['board_pair_repeats.py','background_fixed_worker.py','identity_qualification.py','fixed_arrivals.py','process_cpu.py','collect_results.py']
for name in names:(payload/name).write_bytes((ROOT/'tools'/name).read_bytes())
(payload/'reference40.npz').write_bytes((ROOT/'reference_delivery/results/cpu_reference/all_features.npz').read_bytes());names.append('reference40.npz')
plan['payload_files']=[{'file':name,'bytes':(payload/name).stat().st_size,'sha256':sha(payload/name)}for name in names]
p=ROOT/'protocol/run_v1.json';assert not p.exists();p.write_bytes((json.dumps(plan,indent=2)+'\n').encode());(payload/'run_protocol.json').write_bytes(p.read_bytes())
a=ROOT/'identity_pair_board_input_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for path in sorted(payload.iterdir()):tar.add(path,arcname=path.name,recursive=False)
v={'bytes':a.stat().st_size,'sha256':sha(a),'members':len(names)+1,'protocol_sha256':sha(p),'new_model_forwards':0};(ROOT/'evidence/input_bundle.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
