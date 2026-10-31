set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,numpy as np
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=json.loads((root/'results/terminal.json').read_text());s=json.loads((root/'results/record.json').read_text());p=json.loads((root/'run_protocol.json').read_text())
assert t['status']==s['status']=='ALL_THREE392_SLOT_LOSSLESS_CAPTURE_ENCODING_CONTROLS_COMPLETE' and t['record_sha256']==sha(root/'results/record.json')
assert t['close_error'] is None and not (Path('/proc')/str(t['PID'])).exists() and s['PL_after_sha256']==sha(PL.bitfile_name)==p['O8_bit_sha256']
assert len(s['cases'])==3 and s['actual_O8_forwards']==1170
jobs=[]
for case in ['foreground_with_identity','foreground_idle_identity']:
 folder=root/'results'/case/'background';b=json.loads((folder/'record.json').read_text());terminal=json.loads((folder/'terminal.json').read_text())
 assert terminal['status']==b['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and not (Path('/proc')/str(terminal['PID'])).exists()
 assert terminal['record_sha256']==sha(folder/'record.json') and b['model_forwards']==len(b['jobs'])==11 and b['PNG_compress_level']==0
 jobs.append({'case':case,'actual_jobs':11,'warmups':len(b['warmups']),'mean_crop_photo_save_elapsed_ms':float(np.mean([r['runtime_native_crop_and_photo_save_ms'] for r in b['jobs']])),
 'max_queue_ms':max(r['queue_wait_ms'] for r in b['jobs']),'max_enqueue_to_result_ms':max(r['enqueue_to_result_ms'] for r in b['jobs']),
 'accepted_predictions':sum(r['accepted'] for r in b['jobs'])})
files=[p for p in sorted((root/'results').rglob('*')) if p.is_file()]+[root/r for r in ['run_protocol.json','board_periodic_capture0.py','background_capture0_worker.py','periodic_launch.json','periodic.log']]
manifest=root/'periodic_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in files],indent=2)+'\n')
archive=root/'periodic_delivery.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
final={'PID':t['PID'],'PID_absent':True,'PL_bit_sha256':sha(PL.bitfile_name),'background_processes_absent':True}
print(json.dumps({'transfer':transfer,'cases':[{k:v for k,v in r.items() if k!='periodic_events'} for r in s['cases']],
 'background':jobs,'actual_O8_timed_forwards':1170,'qualification_forwards':s['qualification_forwards'],'O8_warmups':s['warmup_forwards'],'final_read':final,'whole_goal_complete':False}))
PY
