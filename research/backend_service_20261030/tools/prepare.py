from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile,subprocess,sys,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'async_highres_20261030'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
source=(OLD/'tools/board_async_repeats.py').read_text(encoding='utf-8')
def replace(before,after):
 global source
 assert source.count(before)==1,(before,source.count(before));source=source.replace(before,after)
replace('from jpeg_producer import JPEGProducer','from jpeg_producer import JPEGProducer\nfrom process_cpu import snapshot as worker_CPU_snapshot')
replace("concurrent=True;idle_gated=True;causal=True;asynchronous=case=='async_input';requests=ready=None","concurrent=True;idle_gated=case=='idle_gate';causal=True;asynchronous=True;requests=ready=None")
replace("frame=selected[slot]['frame0'];start=time.monotonic_ns()","worker_CPU_before=worker_CPU_snapshot(child.pid)\n    frame=selected[slot]['frame0'];start=time.monotonic_ns()")
replace('    done=time.monotonic_ns()', """    worker_CPU_after=worker_CPU_snapshot(child.pid)
    assert worker_CPU_before['PID']==worker_CPU_after['PID']==child.pid and worker_CPU_before['starttime_ticks']==worker_CPU_after['starttime_ticks']
    assert worker_CPU_before['nice']==worker_CPU_after['nice']==10 and worker_CPU_after['total_CPU_ticks']>=worker_CPU_before['total_CPU_ticks']
    done=time.monotonic_ns()""")
replace("'JPEG_packet_source':packet_record['source'],'JPEG_input_received_monotonic_ns':input_arrived}","'JPEG_packet_source':packet_record['source'],'JPEG_input_received_monotonic_ns':input_arrived,\n      'worker_CPU_before':worker_CPU_before,'worker_CPU_after':worker_CPU_after,'worker_CPU_tick_delta':worker_CPU_after['total_CPU_ticks']-worker_CPU_before['total_CPU_ticks']}")
replace("   if concurrent:\n    os.kill(child.pid,signal.SIGCONT)\n    requests.put(None)","   if concurrent:\n    if idle_gated:os.kill(child.pid,signal.SIGCONT)\n    requests.put(None)")
replace("'ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE'","'ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE'")
runner=ROOT/'tools/board_backend_repeats.py';assert not runner.exists();ast.parse(source);runner.write_text(source,encoding='utf-8')
for name in ['jpeg_producer.py','causal_selector.py','test_producer.py']:shutil.copyfile(OLD/'tools'/name,ROOT/'tools'/name)
worker=(OLD/'tools/background_selected_worker.py').read_text(encoding='utf-8')
old="'execution_policy':'idle_gate','PNG_compress_level':0";assert worker.count(old)==1
worker=worker.replace(old,"'execution_policy':'idle_gate' if protocol['worker_idle_gated'] else 'low_priority_parallel','PNG_compress_level':0,\n  'actual_nice':os.getpriority(os.PRIO_PROCESS,0),'actual_CPU_affinity':sorted(os.sched_getaffinity(0))")
(ROOT/'tools/background_selected_worker.py').write_text(worker,encoding='utf-8');ast.parse(worker)
test=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/test_process_cpu.py')],capture_output=True,text=True);assert test.returncode==0,test.stderr
save(ROOT/'results/CPU_parser_test.json',json.loads(test.stdout))
p=load(OLD/'protocol/run_v1.json');p.update({'status':'FROZEN_BEFORE_FOUR_ASYNC_INPUT_IDLE_VS_LOW_PRIORITY_BACKEND_RUNS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'cases':['idle_gate','low_priority_parallel'],'runs':[{'run':n,'policy':c,'repeat':r} for n,c,r in [('r1_idle_gate','idle_gate',1),('r1_low_priority_parallel','low_priority_parallel',1),('r2_low_priority_parallel','low_priority_parallel',2),('r2_idle_gate','idle_gate',2)]],
 'plan_sha256':sha(ROOT/'计划与验收.md'),'source_runner_sha256':sha(OLD/'tools/board_async_repeats.py'),
 'hypothesis':'nice10 ongoing background may reduce starvation relative to per-frame SIGSTOP with tradeoff measured on foreground',
 'new_boundary_instrumentation':'Same two child/proc/stat CPU-tick snapshots in both policies; clocks include boundary read overhead, not layer-level CPU scheduling trace.',
 'scheduling_only_treatment_between_current_cases':True,'all_current_cases_async_JPEG_producer':True,
 'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False})
names=['board_backend_repeats.py','background_selected_worker.py','jpeg_producer.py','causal_selector.py','test_producer.py','process_cpu.py','test_process_cpu.py']
p['payload_files']=[{'file':n,'sha256':sha(ROOT/'tools'/n),'bytes':(ROOT/'tools'/n).stat().st_size} for n in names]
save(ROOT/'protocol/run_v1.json',p)
archive=ROOT/'payload_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 tar.add(ROOT/'protocol/run_v1.json',arcname='run_protocol.json')
 for name in names:tar.add(ROOT/'tools'/name,arcname=name)
meta={'bytes':archive.stat().st_size,'sha256':sha(archive),'protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'members':len(names)+1};save(ROOT/'results/payload_manifest.json',meta)
launch=(OLD/'tools/launch.sh').read_text(encoding='utf-8');oldmeta=load(OLD/'results/payload_manifest.json')
launch=launch.replace('cow_research_async_highres_20261030','cow_research_backend_service_20261030').replace(oldmeta['sha256'],meta['sha256']).replace(oldmeta['protocol_sha256'],meta['protocol_sha256']).replace('board_async_repeats.py','board_backend_repeats.py')
launch=launch.replace("prior=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_v2_20261030/results/terminal.json')","prior=Path('/home/xilinx/jupyter_notebooks/cow_research_async_highres_20261030/results/terminal.json')")
launch=launch.replace("'test_producer.py']","'test_producer.py','process_cpu.py','test_process_cpu.py']").replace('assert len(tar.getmembers())==6','assert len(tar.getmembers())==8')
marker="(root/'board_producer_behavior_tests.json').write_text(test.stdout)";assert launch.count(marker)==1
launch=launch.replace(marker,marker+"\ntest=subprocess.run([sys.executable,'-B',str(root/'test_process_cpu.py')],cwd=root,capture_output=True,text=True);assert test.returncode==0,test.stderr\n(root/'board_CPU_parser_test.json').write_text(test.stdout)")
(ROOT/'tools/launch.sh').write_text(launch,encoding='utf-8')
for name in ['create_task.sh','status.sh']:
 text=(OLD/'tools'/name).read_text(encoding='utf-8').replace('cow_research_async_highres_20261030','cow_research_backend_service_20261030')
 (ROOT/'tools'/name).write_text(text,encoding='utf-8')
print(json.dumps({'status':p['status'],'CPU_parser_passed':True,**meta}))
