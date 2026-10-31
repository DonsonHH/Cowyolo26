from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,tarfile,subprocess,sys

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'backend_service_20261030'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(name,text):
 if name.endswith('.py'):ast.parse(text)
 p=ROOT/'tools'/name
 if p.exists():assert p.read_bytes()==text.encode(),name
 else:p.write_bytes(text.encode())
 return p
def replace(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)

p=load(OLD/'protocol/run_v1.json');pair=load(PROJECT/'identity_joint_pair_20261030/protocol/run_v1.json')
models=pair['models'];gallery=PROJECT/'identity_joint_pair_20261030/board_delivery/results/identity_qualification/all_features.npz'
models['new']['gallery_SHA256']=sha(gallery);models['old']['gallery_SHA256']=sha(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz')
worker=(OLD/'tools/background_selected_worker.py').read_text()
worker=replace(worker,"root=Path(root);os.nice(protocol['backend_nice_increment'])","root=Path(root);os.sched_setaffinity(0,set(protocol['background_affinity']));os.nice(protocol['backend_nice_increment'])")
worker=replace(worker,'  encoder=Encoder(ENCODER,threads=1)',"  model=protocol['models'][protocol['identity_model']];assert sha(Path(model['encoder_directory'])/'encoder.ncnn.bin')==model['encoder_bin_sha256'];assert sha(model['gallery_features_file'])==model['gallery_SHA256']\n  encoder=Encoder(Path(model['encoder_directory']),threads=1);state['identity_model']=protocol['identity_model'];state['encoder_bin_sha256']=model['encoder_bin_sha256'];state['gallery_features_sha256']=model['gallery_SHA256']")
worker=replace(worker,"with np.load(ENCODER/'vectors_results_v3/all_normalized_features.npz') as a:gallery=a['new_gallery'].astype(np.float64)","with np.load(model['gallery_features_file']) as a:gallery=a[model['gallery_array_key']][:30].astype(np.float64)")
worker=replace(worker,"  ready.put({'status':'READY','PID':os.getpid()})","  state['after_warmup_thread_affinities']={q.name:sorted(os.sched_getaffinity(int(q.name)))for q in Path('/proc/self/task').iterdir()};assert all(mask==protocol['background_affinity']for mask in state['after_warmup_thread_affinities'].values())\n  ready.put({'status':'READY','PID':os.getpid()})")
worker=replace(worker,"   result['completed_monotonic_ns']=time.monotonic_ns();","   result['identity_model']=protocol['identity_model'];result['secondary_Cows_threshold_accepted']=bool(result['similarity']>=protocol['secondary_Cows_threshold']);result['thread_affinities_after_job']={q.name:sorted(os.sched_getaffinity(int(q.name)))for q in Path('/proc/self/task').iterdir()};assert all(mask==protocol['background_affinity']for mask in result['thread_affinities_after_job'].values())\n   result['completed_monotonic_ns']=time.monotonic_ns();")
put('background_selected_worker.py',worker)
main=(OLD/'tools/board_backend_repeats.py').read_text()
main=replace(main,"p=load(ROOT/'run_protocol.json');out=ROOT/'results';out.mkdir(exist_ok=False);cv2.setNumThreads(1)","p=load(ROOT/'run_protocol.json');out=ROOT/'results';out.mkdir(exist_ok=False);cv2.setNumThreads(1);initial_affinity=sorted(os.sched_getaffinity(0));assert initial_affinity==[0,1];os.sched_setaffinity(0,set(p['foreground_affinity']))")
main=replace(main,"'new_training_updates':0,'actual_camera_and_RFID_hardware':False,'whole_goal_complete':False}","'new_training_updates':0,'actual_camera_and_RFID_hardware':False,'whole_goal_complete':False,'foreground_main_thread_affinity':sorted(os.sched_getaffinity(0))}")
main=replace(main,"{**p,'worker_idle_gated':idle_gated}","{**p,'worker_idle_gated':idle_gated,'identity_model':run_spec['identity_model']}")
main=replace(main,"'case':case,'run':run_name,'repeat':run_spec['repeat']","'case':case,'run':run_name,'repeat':run_spec['repeat'],'identity_model':run_spec['identity_model']")
main=replace(main,"'ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE'","'ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE'")
main=replace(main,"  state['memory_after']=Path('/proc/meminfo').read_text();","  os.sched_setaffinity(0,set(initial_affinity));state['main_affinity_restored']=sorted(os.sched_getaffinity(0))\n  state['memory_after']=Path('/proc/meminfo').read_text();")
put('board_trigger_repeats.py',main)
for name in['causal_selector.py','process_cpu.py','test_process_cpu.py','test_producer.py']:put(name,(OLD/'tools'/name).read_text())
producer=(OLD/'tools/jpeg_producer.py').read_text().replace('import threading,time,hashlib,traceback','import threading,time,hashlib,traceback,os')
producer=replace(producer,'    def _run(self):\n        try:','    def _run(self):\n        self.native_TID=threading.get_native_id();self.actual_affinity=sorted(os.sched_getaffinity(0))if hasattr(os,"sched_getaffinity")else None\n        try:')
producer=replace(producer,"'pinned_at_end':self.pinned}","'pinned_at_end':self.pinned,'producer_native_TID':getattr(self,'native_TID',None),'producer_affinity':getattr(self,'actual_affinity',None)}")
put('jpeg_producer.py',producer)
for name in['test_producer.py','test_process_cpu.py']:
 done=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools'/name)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 suffix='.v2'if(ROOT/'results'/(name+'.stderr')).exists()else''
 for ending,data in[('.stdout',done.stdout),('.stderr',done.stderr)]:
  path=ROOT/'results'/(name+suffix+ending);assert not path.exists();path.write_bytes(data)
 assert done.returncode==0,done.stderr.decode()
p.update({'status':'FROZEN_BEFORE_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_CAUSAL_BOARD_RUNS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'runs':[{'run':name,'identity_model':model,'policy':'low_priority_parallel','repeat':repeat}for name,model,repeat in[('r1_old','old',1),('r1_new','new',1),('r2_new','new',2),('r2_old','old',2)]],
 'foreground_affinity':[0,1],'background_affinity':[0,1],'models':models,'secondary_Cows_threshold':pair['secondary_Cows_threshold'],
 'plan_sha256':sha(ROOT/'计划与验收.md'),'source_runner_sha256':sha(OLD/'tools/board_backend_repeats.py'),'source_worker_sha256':sha(OLD/'tools/background_selected_worker.py'),
 'jobs_decoupled_from_current_counter':False,'exactly10_identity_jobs_forced':False,'models_and_corresponding_gallery_only_treatment':True,
 'hypothesis':'Measure actual count-triggered crop selection, actual ARM candidates and foreground/backlog when only the identity encoder with its matched gallery changes.',
 'new_training_updates':0,'new_independent_test':False,'default_model_or_threshold_changed':False,'whole_goal_complete':False,'foreground_affinity_scope':'main thread and observed producer; not every existing library thread',
 'source_latest90_ARM_review_sha256':sha(PROJECT/'identity_final20_arm_20261030/results/final_review.json')})
for obsolete in['background_encoder','model_or_calibration_changed','serial_reads_only_processed_frames','scheduling_only_treatment_between_current_cases']:p.pop(obsolete,None)
p['runtime_files']=pair['runtime_files']+[{'file':models['new']['gallery_features_file'],'sha256':models['new']['gallery_SHA256']}]
for name,model in models.items():assert model['gallery_SHA256']
(ROOT/'protocol').mkdir(exist_ok=False)
collect='''from pathlib import Path
import json,hashlib,tarfile,os,socket,fcntl
from pynq import PL
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_bytes(json.dumps(v,indent=2).encode()+bytes([10]))
p=load(ROOT/'run_protocol.json');s=load(ROOT/'results/record.json');t=load(ROOT/'results/terminal.json')
assert s['status']==t['status']=='ALL4_ACTUAL_COUNT_TRIGGER_OLD_NEW_NEW_OLD_ASYNC_CAUSAL_IDENTITY_RUNS_COMPLETE'and t['record_sha256']==sha(ROOT/'results/record.json')and t['close_error']is None
assert not(Path('/proc')/str(t['PID'])).exists()and s['qualification_forwards']==8 and s['warmup_forwards']==8
children=[]
for spec in p['runs']:
 folder=ROOT/'results'/spec['run']/'background';b=load(folder/'record.json');done=load(folder/'terminal.json')
 assert b['status']==done['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE'and done['record_sha256']==sha(folder/'record.json')and not(Path('/proc')/str(done['PID'])).exists()
 assert b['model_forwards']==len(b['jobs'])and len(b['warmups'])==1
 children.append({'run':spec['run'],'PID':done['PID'],'proc_exists':False,'jobs':len(b['jobs'])})
for row in p['runtime_files']:assert sha(row['file'])==row['sha256']
assert sha(PL.bitfile_name)==p['O8_bit_sha256']
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('r');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
for port in[22,9090]:connection=socket.create_connection(('127.0.0.1',port),timeout=2);connection.close()
save(ROOT/'final_board_state.json',{'status':'ALL_TRIGGER_PAIR_PARENTS_CHILDREN_ABSENT_O8_BOUND_MODELS_GALLERIES_LOCK_AND_LOCAL_SERVICES_VERIFIED','parent_PID':t['PID'],'children':children,'collector_PID':os.getpid(),'PL_SHA256':sha(PL.bitfile_name),'all_runtime_hashes_match':True,'shared_lock_available':True,'local_services':{'22':True,'9090':True},'eth0_carrier':Path('/sys/class/net/eth0/carrier').read_text().strip()})
files=sorted([f for f in(ROOT/'results').rglob('*')if f.is_file()],key=lambda x:(x.suffix,x.name,str(x)))+[ROOT/r['file']for r in p['payload_files']]+[ROOT/name for name in['run_protocol.json','launch.json','run.log','final_board_state.json']]
assert len(files)==len(set(files));rows=[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)}for f in files];save(ROOT/'result_manifest.json',rows)
a=ROOT/'trigger_pair_delivery_v1.tar.xz';assert not a.exists()
with tarfile.open(a,'w:xz',preset=3)as tar:
 for f in files+[ROOT/'result_manifest.json']:tar.add(f,arcname=f.relative_to(ROOT).as_posix(),recursive=False)
os.sync();v={'archive':str(a),'bytes':a.stat().st_size,'sha256':sha(a),'members':len(files)+1,'manifest_files':len(rows)};save(ROOT/'transfer.json',v);save(ROOT/'collection_terminal.json',{'status':'TRIGGER_PAIR_ORIGINAL_ARCHIVE_COMPLETE','PID':os.getpid(),'transfer':v});print(json.dumps(v),flush=True)
'''
put('collect_results.py',collect)
names=['board_trigger_repeats.py','background_selected_worker.py','jpeg_producer.py','causal_selector.py','process_cpu.py','collect_results.py']
payload=ROOT/'payload';payload.mkdir(exist_ok=False)
for name in names:(payload/name).write_bytes((ROOT/'tools'/name).read_bytes())
p['payload_files']=[{'file':n,'sha256':sha(payload/n),'bytes':(payload/n).stat().st_size}for n in names]
file=ROOT/'protocol/run_v1.json';file.write_bytes(json.dumps(p,indent=2).encode()+bytes([10]));(payload/'run_protocol.json').write_bytes(file.read_bytes())
a=ROOT/'trigger_pair_input_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz')as tar:
 for f in sorted(payload.iterdir()):tar.add(f,arcname=f.name,recursive=False)
v={'bytes':a.stat().st_size,'sha256':sha(a),'members':7,'protocol_sha256':sha(file),'new_model_forwards':0};(ROOT/'evidence/input_bundle.json').write_bytes(json.dumps(v,indent=2).encode()+bytes([10]));print(json.dumps(v))
