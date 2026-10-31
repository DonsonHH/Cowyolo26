from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
verified=load(ROOT/'results/independent_verification.json');assert verified['actual_background_identity_jobs']==11 and verified['cases'][1]['skipped_slots']==3
out=PROJECT/'pynq_idle_control_20261030';out.mkdir(exist_ok=False)
for d in ['tools','protocol','results','evidence']:(out/d).mkdir()
background=(ROOT/'tools/background_worker_v2.py').read_text()
background=background.replace("'PL_actions':0,'whole_goal_complete':False}","'PL_actions':0,'whole_goal_complete':False,'execution_policy':'Parentstopsworkerduringforegroundcriticalsectionandresumesinslack'}")
background=background.replace("start=time.monotonic_ns();frame=job['source_frame0']", "start=time.monotonic_ns();cpu_start=time.process_time_ns();frame=job['source_frame0']")
background=background.replace("preprocessed=time.monotonic_ns();raw=encoder.run(x)","preprocessed=time.monotonic_ns();network_cpu_start=time.process_time_ns();raw=encoder.run(x)")
background=background.replace("inferred=time.monotonic_ns()", "inferred=time.monotonic_ns();network_cpu_end=time.process_time_ns()")
background=background.replace("'actual_identity_network_ms':(inferred-preprocessed)/1e6,", "'actual_identity_network_ms':(inferred-preprocessed)/1e6,'identity_network_process_CPU_ms':(network_cpu_end-network_cpu_start)/1e6,")
background=background.replace("result['completed_monotonic_ns']=time.monotonic_ns();", "result['completed_monotonic_ns']=time.monotonic_ns();result['worker_process_CPU_ms']=(time.process_time_ns()-cpu_start)/1e6;")
(out/'tools/background_idle_worker.py').write_text(background,newline='\n');ast.parse(background)
text=(ROOT/'tools/board_periodic_v2.py').read_text()
text=text.replace('multiprocessing,traceback','multiprocessing,traceback,signal')
text=text.replace('from background_worker_v2 import worker','from background_idle_worker import worker')
text=text.replace("out=ROOT/'results'","out=ROOT/'results'")
text=text.replace("for row in load(ROOT/'camera/manifest.json'):assert sha(ROOT/'camera'/row['file'])==row['sha256']", "for row in load(Path(p['camera_root'])/'manifest.json'):assert sha(Path(p['camera_root'])/row['file'])==row['sha256']")
text=text.replace("for case in p['cases']:","for case in p['cases']:")
text=text.replace("concurrent=case=='foreground_with_identity'","concurrent=case in ['foreground_with_identity','foreground_idle_identity']")
text=text.replace("str(folder/'background'),str(ROOT),p", "str(folder/'background'),str(Path(p['camera_root']).parent),p")
text=text.replace("slot=0\n   while slot<392:", "slot=0;worker_pauses=[]\n   while slot<392:")
marker="    frame=selected[slot]['frame0'];start=time.monotonic_ns();actual=graph.run_image(framebank[slot]).copy();state['actual_O8_forwards']+=1"
assert text.count(marker)==1
replacement='''    pause_request=pause_ack=None
    if concurrent:
     pause_request=time.monotonic_ns();os.kill(child.pid,signal.SIGSTOP)
     stopped_pid,stopped_status=os.waitpid(child.pid,os.WUNTRACED)
     pause_ack=time.monotonic_ns();assert stopped_pid==child.pid and os.WIFSTOPPED(stopped_status)
    frame=selected[slot]['frame0'];start=time.monotonic_ns();actual=graph.run_image(framebank[slot]).copy();state['actual_O8_forwards']+=1'''
text=text.replace(marker,replacement)
marker="    done=time.monotonic_ns()\n    rows.append(";assert text.count(marker)==1
text=text.replace(marker,"""    done=time.monotonic_ns()
    if concurrent:
     os.kill(child.pid,signal.SIGCONT);resumed=time.monotonic_ns()
     worker_pauses.append({'slot':slot,'pause_requested_monotonic_ns':pause_request,'pause_acknowledged_monotonic_ns':pause_ack,
       'foreground_started_monotonic_ns':start,'foreground_completed_monotonic_ns':done,'resume_sent_monotonic_ns':resumed,'child_PID':child.pid})
    rows.append(""")
text=text.replace("   if concurrent:\n    requests.put(None);", "   if concurrent:\n    os.kill(child.pid,signal.SIGCONT)\n    requests.put(None);")
text=text.replace("write(folder/'timing_rows.json',rows);", "write(folder/'worker_pause_intervals.json',worker_pauses);write(folder/'timing_rows.json',rows);")
text=text.replace("   if child.is_alive():\n    try:requests.put_nowait(None)", "   if child.is_alive():\n    try:os.kill(child.pid,signal.SIGCONT)\n    except Exception:pass\n    try:requests.put_nowait(None)")
text=text.replace("'BOTH392_SLOT_PERIODIC_FRONTEND_CASES_AND_ACTUAL_TRIGGERED_BACKGROUND_COMPLETE'","'BOTH392_SLOT_FOREGROUND_AND_IDLE_GATED_IDENTITY_CASES_COMPLETE'")
text=text.replace("'foreground_warmups'","'foreground_warmups'")
file=out/'tools/board_idle.py';file.write_text(text,newline='\n');ast.parse(text)
# Only scheduling changes: all actual frontend/network/photo/retrieval logic remains.
protocol=load(ROOT/'delivery/protocol.json')
protocol.update({'status':'FROZEN_BEFORE_IDLE_GATED_CONTROL_RUN','created_UTC':datetime.now(timezone.utc).isoformat(),
 'cases':['foreground_only','foreground_idle_identity'],'camera_root':'/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030/camera',
 'previous_both_cases_review_sha256':sha(ROOT/'results/independent_verification.json'),
 'scheduling_intervention':'Onlyoneactualworkerprocess:SIGSTOPandwaitackbeforeeachforeground;SIGCONTafterrecordedcountcompletion. Networkresumesfromactualcomputeinsideidlewindows.',
 'all_other_input_model_threshold_gallery_photo_stage_and_periodic_rules_unchanged':True,
 'record_worker_process_CPU_and_network_CPU_ms':True,'model_and_calibration_changes':False,
 'payload_files':[{'file':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in [file,out/'tools/background_idle_worker.py']]})
protocolfile=out/'protocol/run_v1.json';protocolfile.write_text(json.dumps(protocol,indent=2)+'\n')
archive=out/'payload.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for f,name in [(file,'board_idle.py'),(out/'tools/background_idle_worker.py','background_idle_worker.py'),(protocolfile,'protocol.json')]:tar.add(f,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':3,'protocol_sha256':sha(protocolfile)}
(out/'evidence/payload.json').write_text(json.dumps(meta,indent=2)+'\n')
(out/'计划与验收.md').write_text('''# 同板后台空闲间隙调度：固定单因素对照

上一轮前台独占392／392、23迟到；并行后台389／392、3跳帧、128迟到，两个条件计数均11。11张照片和真实身份网络确实在同一块PYNQ运行，尚不能证明每帧稳定5Hz。

本轮只改变后台调度：在每次前台关键处理前，对唯一自有身份进程发SIGSTOP并等待操作系统确认；前台完成计数后SIGCONT，让真实高分辨率解码、照片保存、预处理和身份网络在剩余间隙推进。记录每一停止／恢复区间和进程CPU时间；不使用替代特征、缓存结果或虚假等待。

保留前台独占为本轮控制。其余392时隙、同帧高分辨率输入、图、阈值、计数器、图库和全未读RFID模拟条件均保持，不因结果改变。需要比较跳帧、释放到计数截止时间、11头开发结果、后台队列及实际检索耗时。若仍不满足时序，保留失败而不是替换历史数据。

这一Linux用户态调度控制不会代表实际摄像头／RFID已连接或永久身份准确率已验证。整体科研继续，原640人工12头版本保持。
''',encoding='utf-8')
target='/home/xilinx/jupyter_notebooks/cow_research_idle_control_20261030'
create='''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
p=Path('TARGET');p.mkdir(exist_ok=False);print(json.dumps({'created':str(p)}))
PY
'''.replace('TARGET',target)
(out/'tools/create_task.sh').write_text(create,newline='\n')
launch='''set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,os,sys,subprocess
root=Path('TARGET');old=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030')
t=json.loads((old/'results/terminal.json').read_text());assert t['status']=='BOTH392_SLOT_PERIODIC_FRONTEND_CASES_AND_ACTUAL_TRIGGERED_BACKGROUND_COMPLETE' and not (Path('/proc')/str(t['PID'])).exists()
archive=root/'payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['protocol.json','board_idle.py','background_idle_worker.py']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'run.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_idle.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
record={'PID':child.pid,'cases':2,'slots_per_case':392,'actual_identity_process_SIGSTOP_SIGCONT_gate':True,'cached_identity_results_used':False}
(root/'launch.json').write_text(json.dumps(record,indent=2)+'\\n');print(json.dumps(record))
PY
'''.replace('TARGET',target).replace('DIGEST',meta['sha256'])
(out/'tools/launch_board.sh').write_text(launch,newline='\n')
status=(ROOT/'tools/status_board.sh').read_text().replace('cow_research_periodic_joint_20261030','cow_research_idle_control_20261030')
(out/'tools/status_board.sh').write_text(status,newline='\n');print(json.dumps({'phase':str(out),'payload':meta}))
