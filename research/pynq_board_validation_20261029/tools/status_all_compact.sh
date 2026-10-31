set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029');rows=[]
for run in ['probe192','formal192','formal256','formal320']:
    launchfile=root/('launch_'+run+'.json')
    if not launchfile.exists():rows.append({'run':run,'started':False});continue
    launch=json.loads(launchfile.read_text());pid=launch['PID'];terminal=root/run/'terminal.json';progress=root/run/'progress.json'
    r={'run':run,'PID':pid,'ps':subprocess.run(['ps','-p',str(pid),'-o','pid,state,etimes,rss,comm'],capture_output=True,text=True).stdout,
       'progress':json.loads(progress.read_text()) if progress.exists() else None,'terminal':json.loads(terminal.read_text()) if terminal.exists() else None}
    if terminal.exists():
        data=json.loads((root/run/'record.json').read_text());r.update({k:data.get(k) for k in ['status','detector_e2e_statistics','photo_rotation_detector_statistics','fixed_E010_detector_statistics','close_error','detail']})
        r['cow_present_photos']=sum(bool(q['cow_boxes_rotated_native']) for q in data['rows'][:12])
    else:r['log_tail']=(root/(run+'.log')).read_text(errors='replace')[-1000:]
    rows.append(r)
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'profiles':rows}))
PY
