set -euo pipefail
test "$(id -un)" = root
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,os
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_mosaic192_joint_20261030')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=json.loads((root/'results/record.json').read_text());t=json.loads((root/'results/terminal.json').read_text());p=json.loads((root/'run_protocol.json').read_text())
assert s['status']==t['status']=='ALL_SIX392_SLOT_MOSAIC192_SAME_BOARD_REPEATS_COMPLETE'
assert t['record_sha256']==sha(root/'results/record.json') and t['close_error'] is None and not (Path('/proc')/str(t['PID'])).exists()
assert s['actual_O8_forwards']==sum(r['processed_frames'] for r in s['cases']) and len(s['cases'])==6
assert s['qualification_forwards']==8 and s['warmup_forwards']==12 and s['PL_after_sha256']==p['O8_bit_sha256']==sha(PL.bitfile_name)
children=[]
for run in p['runs']:
 if run['policy']=='foreground_only':continue
 folder=root/'results'/run['run']/'background';bt=json.loads((folder/'terminal.json').read_text());b=json.loads((folder/'record.json').read_text())
 assert bt['status']==b['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and bt['record_sha256']==sha(folder/'record.json')
 assert not (Path('/proc')/str(bt['PID'])).exists();assert len(b['jobs'])==b['model_forwards']
 children.append({'PID':bt['PID'],'proc_exists':False,'jobs':len(b['jobs']),'run':run['run']})
f=root/'final_state.json';assert not f.exists();f.write_text(json.dumps({'status':'SIX_RUN_PARENT_AND_FOUR_IDENTITY_WORKERS_TERMINAL_ABSENT_O8_RETAINED','PID':t['PID'],'proc_exists':False,
 'children':children,'PL_bitfile':PL.bitfile_name,'PL_bit_sha256':sha(PL.bitfile_name),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'memory':Path('/proc/meminfo').read_text(),'new_network_forwards_in_collection':0},indent=2)+'\n')
files=[f for f in sorted((root/'results').rglob('*')) if f.is_file()]
files.extend(root/name for name in ['run_protocol.json','board_joint_repeats.py','background_capture0_worker.py','launch.json','run.log','final_state.json'])
manifest=root/'result_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
a=root/'joint_results_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
os.sync()
r={'archive':str(a),'bytes':a.stat().st_size,'sha256':sha(a),'members':len(files)+1,'manifest_files':len(files)}
(root/'transfer.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'transfer':r,'actual_O8_forwards':s['actual_O8_forwards'],'cases':s['cases'],'children':children,'whole_goal_complete':False}))
PY
