from pathlib import Path
import json,os,time
root=Path('/home/xilinx/jupyter_notebooks/cow_research_lowres_20261029')
launch=json.loads((root/'launch.json').read_text());pid=launch['PID'];proc=Path('/proc')/str(pid)
result={'PID':pid,'process_exists':proc.exists(),'status':None,'process_state':None,'progress':None}
if proc.exists():
    try:result['process_state']=[s for s in (proc/'status').read_text().splitlines() if s.startswith(('State','VmRSS','Threads'))]
    except Exception as e:result['process_read_error']=type(e).__name__
for rel in ['results/progress.json','results/summary.json']:
    path=root/rel
    if path.exists():
        obj=json.loads(path.read_text())
        if rel.endswith('summary.json'):
            result['status']=obj['status'];result['summary']={k:v for k,v in obj.items() if k not in ['phases','PL_before_IP_names','PL_after_IP_names']}
            result['completed_phases']=[{k:v for k,v in p.items() if k not in ['rows']} for p in obj['phases']]
        else:result['progress']=obj
log=root/'benchmark.log'
if log.exists():result['log_tail']=log.read_text(errors='replace')[-3500:]
print(json.dumps(result))
