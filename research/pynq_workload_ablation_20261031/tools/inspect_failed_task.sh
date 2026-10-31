set -euo pipefail
test "$(id -un)" = xilinx
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json
root=Path('/home/xilinx/jupyter_notebooks/cow_research_workload_ablation_20261031')
state=json.loads((root/'results/record.json').read_text())
children=[]
for folder in sorted((root/'results').iterdir()):
 if not folder.is_dir():continue
 row={'run':folder.name,'files':[p.name for p in folder.iterdir()]}
 for name in ['record','terminal']:
  path=folder/'background'/(name+'.json')
  if path.exists():
   value=json.loads(path.read_text());row['background_'+name]={k:v for k,v in value.items()if k not in ['jobs']}
   if name=='record':row['background_jobs']=len(value.get('jobs',[]))
 children.append(row)
processes=[]
for path in Path('/proc').iterdir():
 if not path.name.isdigit():continue
 try:
  args=(path/'cmdline').read_bytes().split(bytes([0]))
  if any(b'cow_research_workload_ablation_20261031' in arg for arg in args):
   processes.append({'PID':int(path.name),'args':[arg.decode(errors='replace') for arg in args], 'stat':(path/'stat').read_text()})
 except (OSError,PermissionError):pass
print(json.dumps({'state':{k:v for k,v in state.items()if k not in ['cases','initialization','qualification_gate']},
                  'case_count':len(state['cases']),'run_folders':children,'task_processes':processes,
                  'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                  'meminfo':Path('/proc/meminfo').read_text(),'log_tail':(root/'run.log').read_text()[-3000:]}),flush=True)
PY
