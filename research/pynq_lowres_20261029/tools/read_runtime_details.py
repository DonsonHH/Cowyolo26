from pathlib import Path
import json,hashlib
root=Path('/home/xilinx/jupyter_notebooks');rows=[]
paths=[
'yolo26_optimization_8/device_initialize.py','yolo26_optimization_8/native_graph.py','yolo26_optimization_8/verify_release.py',
'yolo26_optimization_8/selected_candidates.json','yolo26_optimization_8/README_reproduce.md',
'yolo26_optimization_8/hardware/accepted/firmware_manifest.json','yolo26_optimization_8/runtime_fast/queue_device.py',
'yolo26_optimization_8/reports/closure_status.json','yolo26_optimization_8/reports/final_board_environment.json',
'yolo26_optimization_8/program_r192/manifest.json','yolo26_optimization_8/program_r256/manifest.json',
'yolo26_optimization_8/plans/selected.json','yolo26_optimization_6/r192/model/graph.json',
'yolo26_optimization_6/r256/model/graph.json','yolo26_optimization_6/r320/model/graph.json',
'yolo26_optimization_6/runtime_fast/queue_device.py',
'yolo26_optimization_6/runs/r192_fast_acceptance100/result.json',
'yolo26_optimization_6/runs/r256_fixed100/result.json','yolo26_optimization_6/runs/r320_fixed100/result.json']
for rel in paths:
    f=root/rel
    if f.is_file() and f.stat().st_size<=700000:
        raw=f.read_bytes();rows.append({'path':str(f),'relative':rel,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'text':raw.decode('utf-8','replace')})
folders={}
for rel in ['yolo26_optimization_8/hardware/accepted','yolo26_optimization_8/reports/final_delivery','yolo26_optimization_8/program_r192',
            'yolo26_optimization_6/r320/model']:
    d=root/rel
    if d.is_dir():folders[rel]=[{'name':f.name,'bytes':f.stat().st_size if f.is_file() else None,'directory':f.is_dir()} for f in sorted(d.iterdir())]
print(json.dumps({'sources':rows,'directories':folders}))
