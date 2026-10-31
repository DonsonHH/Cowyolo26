set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_startup_probe_20261031')
load=lambda path:json.loads(path.read_text())if path.exists()else None
launch=load(root/'launch.json');state=load(root/'results/record.json')or{}
def kb(text,key):
 return next(int(line.split()[1])for line in text.splitlines()if line.startswith(key+':'))
cases=[]
for case in state.get('runs',[]):
 folder=root/'results'/case['run'];p=load(folder/'record.json');w=load(folder/'background/record.json')
 if p is None or w is None:continue
 t=w.get('startup_probe',{})
 row={'run':case['run'],'parent_exitcode':case['parent_exitcode'],'ready_wait_40s_expired':p.get('ready_wait_40s_expired'),
      'identity_warmups':len(w['warmups']),'formal_identity_jobs':w['model_forwards']}
 if 'child_at_READY'in p:
  row.update({'start_to_READY_ms':(p['ready_received_monotonic_ns']-p['before_child_start_monotonic_ns'])/1e6,
              'child_Pss_kB':kb(p['child_at_READY']['smaps_rollup'],'Pss'),
              'parent_Pss_kB':kb(p['parent_at_READY']['smaps_rollup'],'Pss'),
              'child_module_import_ms':(t['module_end_monotonic_ns']-t['module_begin_monotonic_ns'])/1e6,
              'encoder_init_ms':(t['after_encoder_init_monotonic_ns']-t['before_encoder_init_monotonic_ns'])/1e6,
              'READY_put_to_parent_ms':(p['ready_received_monotonic_ns']-t['before_READY_put_monotonic_ns'])/1e6,
              'pynq_imported':t['pynq_imported'],'cv2_imported':t['cv2_imported']})
 cases.append(row)
print(json.dumps({'controller_PID':launch['PID'],'controller_proc_exists':(Path('/proc')/str(launch['PID'])).exists(),
 'terminal':load(root/'results/terminal.json'),'progress':load(root/'results/progress.json'),'cases':cases,
 'log_tail':(root/'controller.log').read_text()[-1500:]}),flush=True)
PY
