from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'pynq_idle_control_20261030'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
bench=load(ROOT/'results/encoding_verification.json');assert bench['pixel_identical_photo_pairs']==11 and bench['mean_wall_speed_ratio_level6_vs0']>7
backend=(OLD/'tools/background_idle_worker.py').read_text();assert backend.count('photo.save(photo_file)')==1
backend=backend.replace('photo.save(photo_file)','photo.save(photo_file,compress_level=0)')
backend=backend.replace("'execution_policy':'Parentstopsworkerduringforegroundcriticalsectionandresumesinslack'", "'execution_policy':'idle_gate' if protocol.get('worker_idle_gated') else 'direct_background','PNG_compress_level':0")
file=ROOT/'tools/background_capture0_worker.py';file.write_text(backend,newline='\n');ast.parse(backend)
front=(OLD/'tools/board_idle.py').read_text().replace('from background_idle_worker import','from background_capture0_worker import')
front=front.replace("ROOT/'protocol.json'","ROOT/'run_protocol.json'")
front=front.replace("concurrent=case in ['foreground_with_identity','foreground_idle_identity']","concurrent=case in ['foreground_with_identity','foreground_idle_identity'];idle_gated=case=='foreground_idle_identity'")
front=front.replace("str(Path(p['camera_root']).parent),p", "str(Path(p['camera_root']).parent),{**p,'worker_idle_gated':idle_gated}")
front=front.replace("    if concurrent:\n     pause_request=", "    if idle_gated:\n     pause_request=")
front=front.replace("    if concurrent:\n     os.kill(child.pid,signal.SIGCONT);resumed=", "    if idle_gated:\n     os.kill(child.pid,signal.SIGCONT);resumed=")
front=front.replace("assert len(state['cases'])==2", "assert len(state['cases'])==3")
front=front.replace('BOTH392_SLOT_FOREGROUND_AND_IDLE_GATED_IDENTITY_CASES_COMPLETE','ALL_THREE392_SLOT_LOSSLESS_CAPTURE_ENCODING_CONTROLS_COMPLETE')
runner=ROOT/'tools/board_periodic_capture0.py';runner.write_text(front,newline='\n');ast.parse(front)
p=load(OLD/'protocol/run_v1.json');p.update({'status':'FROZEN_BEFORE_ALL_THREE392_SLOT_CAPTURE_ENCODING_CONTROLS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'cases':['foreground_only','foreground_with_identity','foreground_idle_identity'],'PNG_compress_level':0,
 'independent_board_encoding_benchmark_sha256':sha(ROOT/'results/encoding_verification.json'),
 'fixed_intervention':'OnlyPillowphotoPNGcompress_level0insteaddefault6. Decodedphotopixelsandnetworkinputmustmatch;weights,sourceframes,counter,RFIDsimulation,gallery,thresholdallunchanged.',
 'file_storage_tradeoff':'About3xencodedbytesinthe22writebenchmark;actualpipelinefilesizesrecorded.',
 'three_cases_single_run_each_not_statistical_significance':True,
 'payload_files':[{'file':f.name,'sha256':sha(f),'bytes':f.stat().st_size} for f in [file,runner]],
 'previous_idle_validation_sha256':sha(OLD/'results/idle_gate_verification.json'),
 'backend_runtime_photo_pixel_and_input_parity_against_prior_required':True})
protocol=ROOT/'protocol/periodic_v1.json';protocol.write_text(json.dumps(p,indent=2)+'\n')
archive=ROOT/'periodic_payload.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for source,name in [(file,file.name),(runner,runner.name),(protocol,'run_protocol.json')]:tar.add(source,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':3,'protocol_sha256':sha(protocol)}
(ROOT/'evidence/periodic_payload.json').write_text(json.dumps(meta,indent=2)+'\n')
launch='''set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,sys,os
root=Path('/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030');t=json.loads((root/'encoding_results/terminal.json').read_text());assert t['success'] and not (Path('/proc')/str(t['PID'])).exists()
assert not (root/'results').exists() and not (root/'periodic_launch.json').exists()
archive=root/'periodic_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['run_protocol.json','board_periodic_capture0.py','background_capture0_worker.py']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'periodic.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-X','faulthandler','-u','-B',str(root/'board_periodic_capture0.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'cases':3,'offered_slots_each':392,'actual_PNG_compress_level':0,'lossless_pixels_unchanged':True}
(root/'periodic_launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('DIGEST',meta['sha256'])
(ROOT/'tools/launch_periodic.sh').write_text(launch,newline='\n')
status=(OLD/'tools/status_board.sh').read_text().replace('cow_research_idle_control_20261030','cow_research_capture_encoding_20261030').replace("root/'launch.json'","root/'periodic_launch.json'").replace("root/'run.log'","root/'periodic.log'")
(ROOT/'tools/status_periodic.sh').write_text(status,newline='\n')
(ROOT/'计划与验收.md').write_text('''# 抓拍保存开销与同板5Hz验证

先对全部11张已实测照片，交替顺序保存PNG6和PNG0各一次，22次实际板上文件保存的解码像素完全相同。保存平均732→100ms，文件总量约3倍。微基准只解释保存阶段，不直接替代整链性能。

随后只改变照片保存的PNG压缩级别，保留前台独占、直接后台和空闲后台三个392时隙控制。每个处理时刻仍执行真实O8模型，后台仍用实时框、同帧高分辨率图、原Pillow几何、真实NCNN网络及同一图库阈值；保存照片像素和实际输入再与此前结果配对验证。

全部跳帧、200ms迟到、计数11与人审12差距、后台队列和文件体积均报告。三个条件各单次运行，保留前次全部基线，不作统计显著性推断。公开图像回放和RFID全未应答为模拟，不代表现场设备已连接或身份准确率已验证。
''',encoding='utf-8')
print(json.dumps(meta))
