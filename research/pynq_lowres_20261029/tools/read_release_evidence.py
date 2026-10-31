from pathlib import Path
import json,hashlib
root=Path('/home/xilinx/jupyter_notebooks');out={'reports':[],'metadata':[],'sources':[]}
for rel in ['yolo26_optimization_8/reports/final_delivery/summary.json','yolo26_optimization_8/reports/final_delivery/candidate_pareto.csv',
'yolo26_optimization_8/reports/final_delivery/README_reproduce.md','yolo26_optimization_8/reports/final_delivery/math_and_source_integrity.json',
'yolo26_optimization_8/reports/long_camera_summary_1746753240416977189.json','yolo26_optimization_8/reports/final_delivery/completion_final_audit.json']:
    file=root/rel
    if file.is_file() and file.stat().st_size<200000:
        raw=file.read_bytes();out['reports'].append({'relative':rel,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode('utf-8','replace')})
for rel in ['yolo26_optimization_8/program_r192/program.json','yolo26_optimization_8/program_r256/program.json',
'yolo26_optimization_6/r320/model/graph.json','yolo26_optimization_6/runtime/queue_overlay_manifest.json','yolo26_optimization_8/release_manifest.json']:
    file=root/rel
    if file.is_file():
        raw=file.read_bytes();obj=json.loads(raw);summary={k:v for k,v in obj.items() if k not in ['nodes','shapes','names','tensors','runtime_files','reproduction_files','conv_specs']}
        out['metadata'].append({'relative':rel,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'keys':list(obj),'summary':summary})
for rel in ['yolo26_optimization_6/runtime/queue_conv.py','yolo26_optimization_6/runtime/hybrid_executor.py',
            'yolo26_optimization_6/runtime/native_ops.py','yolo26_optimization_6/runtime/queue_device.py']:
    file=root/rel;raw=file.read_bytes();out['sources'].append({'relative':rel,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'text':raw.decode('utf-8','replace')})
print(json.dumps(out))
