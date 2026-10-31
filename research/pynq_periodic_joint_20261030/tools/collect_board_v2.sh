set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,tarfile,hashlib,subprocess
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=json.loads((root/'results/terminal.json').read_text());s=json.loads((root/'results/record.json').read_text())
assert t['status']==s['status']=='BOTH392_SLOT_PERIODIC_FRONTEND_CASES_AND_ACTUAL_TRIGGERED_BACKGROUND_COMPLETE'
assert t['record_sha256']==sha(root/'results/record.json') and not (Path('/proc')/str(t['PID'])).exists() and t['close_error'] is None
assert len(s['cases'])==2 and s['hardware_status']['error']=='0x0' and s['PL_after_sha256']==sha(PL.bitfile_name)
background=root/'results/foreground_with_identity/background';bt=json.loads((background/'terminal.json').read_text());bs=json.loads((background/'record.json').read_text())
assert bt['status']==bs['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and not (Path('/proc')/str(bt['PID'])).exists()
assert bt['record_sha256']==sha(background/'record.json') and bt['model_forwards']==bs['model_forwards']==len(bs['jobs'])
files=[p for p in sorted((root/'results').rglob('*')) if p.is_file()]
files.extend(root/r for r in ['protocol_template.json','protocol_template_v2.json','protocol.json','board_periodic.py','board_periodic_v2.py','background_worker.py','background_worker_v2.py','launch.json','run.log'])
manifest=root/'result_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root/'results_delivery.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
(root/'results_transfer.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'transfer':r,'cases':s['cases'],'actual_O8_timed_forwards':s['actual_O8_forwards'],'qualification_forwards':s['qualification_forwards'],
 'foreground_warmups':s['warmup_forwards'],'actual_background_model_forwards':bs['model_forwards'],'background_warmups':len(bs['warmups']),
 'background_accepted_IDs':sum(j['accepted'] for j in bs['jobs']),'maximum_background_queue_wait_ms':max([j['queue_wait_ms'] for j in bs['jobs']]+[0]),
 'background_identity_labels_available':False,'whole_goal_complete':False}))
PY
