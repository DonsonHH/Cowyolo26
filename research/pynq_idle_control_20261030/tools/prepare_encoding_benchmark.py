from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'pynq_capture_encoding_20261030';ROOT.mkdir(exist_ok=False)
for d in ['tools','protocol','results','evidence']:(ROOT/d).mkdir()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=PROJECT/'pynq_periodic_joint_20261030';bg=old/'delivery/results/foreground_with_identity/background';jobs=json.loads((bg/'record.json').read_text())['jobs']
p={'status':'FROZEN_BEFORE_ACTUAL_BOARD_LOSSLESS_ENCODING_MICROBENCHMARK','created_UTC':datetime.now(timezone.utc).isoformat(),
 'source_case':'Earlierdirectconcurrencyall11actualphotos','photos':[{'file':j['photo_file'],'sha256':j['photo_sha256']} for j in jobs],
 'levels':[6,0],'source_pixels_unchanged':True,'order':'Evenindex6then0,oddindex0then6;all11photosincluded,eachlevelonce.',
 'timing_scope':'AlreadydecodedRGBphoto->PillowPNG.saveactualnewfile;redecodepixelcheckoutsideclock;CPUandwallrecorded.',
 'is_new_identity_accuracy_test':False,'new_model_forwards':0,'new_training_updates':0,'PL_actions':0,'whole_goal_complete':False}
file=ROOT/'protocol/encoding_v1.json';file.write_text(json.dumps(p,indent=2)+'\n')
code='''from pathlib import Path
import os,json,time,hashlib,traceback,sys
from PIL import Image
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads((ROOT/'protocol.json').read_text());out=ROOT/'encoding_results';out.mkdir(exist_ok=False);rows=[]
source=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030/results/foreground_with_identity/background')
try:
 for i,row in enumerate(p['photos']):
  file=source/row['file'];assert sha(file)==row['sha256']
  with Image.open(file) as im:im.load();photo=im.convert('RGB')
  expected=hashlib.sha256(photo.tobytes()).hexdigest()
  for level in ([6,0] if i%2==0 else [0,6]):
   path=out/('photo'+str(i).zfill(2)+'_level'+str(level)+'.png')
   cpu=time.process_time_ns();start=time.monotonic_ns();photo.save(path,compress_level=level);end=time.monotonic_ns();cpu_end=time.process_time_ns()
   with Image.open(path) as observed:observed.load();assert observed.size==photo.size and hashlib.sha256(observed.convert('RGB').tobytes()).hexdigest()==expected
   record={'photo_index':i,'source_file':row['file'],'PNG_compress_level':level,'encode_file_wall_ms':(end-start)/1e6,
    'encode_file_CPU_ms':(cpu_end-cpu)/1e6,'output_file':path.name,'output_bytes':path.stat().st_size,'output_sha256':sha(path),'decoded_RGB_sha256':expected,'pixels_exact':True}
   rows.append(record);print(json.dumps(record),flush=True)
 result={'status':'ALL11_PHOTOS_TWO_LOSSLESS_PNG_ENCODINGS_ACTUALLY_MEASURED','PID':os.getpid(),'rows':rows,'new_model_forwards':0,'PL_actions':0,'whole_goal_complete':False}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\\n')
except BaseException as e:
 (out/'failure.json').write_text(json.dumps({'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\\n');raise
finally:
 (out/'terminal.json').write_text(json.dumps({'PID':os.getpid(),'success':(out/'summary.json').exists(),'rows':len(rows)},indent=2)+'\\n')
'''
(ROOT/'tools/board_benchmark.py').write_text(code,newline='\n')
archive=ROOT/'benchmark_payload.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for file,name in [(ROOT/'tools/board_benchmark.py','board_benchmark.py'),(ROOT/'protocol/encoding_v1.json','protocol.json')]:tar.add(file,arcname=name,recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':2,'protocol_sha256':sha(ROOT/'protocol/encoding_v1.json')}
(ROOT/'evidence/benchmark_payload.json').write_text(json.dumps(meta,indent=2)+'\n')
target='/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030'
(ROOT/'tools/create_task.sh').write_text('''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json
p=Path('TARGET');p.mkdir(exist_ok=False);print(json.dumps({'created':str(p)}))
PY
'''.replace('TARGET',target),newline='\n')
(ROOT/'tools/launch_benchmark.sh').write_text('''set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess,os,sys
root=Path('TARGET');old=Path('/home/xilinx/jupyter_notebooks/cow_research_idle_control_20261030');t=json.loads((old/'results/terminal.json').read_text());assert not (Path('/proc')/str(t['PID'])).exists()
archive=root/'benchmark_payload.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='DIGEST'
with tarfile.open(archive) as tar:
 for m in tar.getmembers():
  assert m.isfile() and m.name in ['protocol.json','board_benchmark.py']
  p=root/m.name;assert not p.exists();p.write_bytes(tar.extractfile(m).read())
with (root/'benchmark.log').open('xb') as log:
 child=subprocess.Popen([sys.executable,'-u','-B',str(root/'board_benchmark.py')],cwd=root,stdout=log,stderr=subprocess.STDOUT,env=os.environ.copy(),start_new_session=True)
r={'PID':child.pid,'photo_encodes':22,'actual_model_forwards':0};(root/'benchmark_launch.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r))
PY
'''.replace('TARGET',target).replace('DIGEST',meta['sha256']),newline='\n')
print(json.dumps({'phase':str(ROOT),'payload':meta}))
