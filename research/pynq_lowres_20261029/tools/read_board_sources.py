from pathlib import Path
import json,hashlib,os
root=Path('/home/xilinx/jupyter_notebooks');out={'topfiles':{},'source_files':[],'selected_reports':[]}
for name in ['yolo26_optimization_6','yolo26_optimization_7','yolo26_optimization_8']:
    folder=root/name
    if not folder.exists():continue
    out['topfiles'][name]=[{'name':p.name,'bytes':p.stat().st_size if p.is_file() else None,'directory':p.is_dir()} for p in sorted(folder.iterdir()) if not p.name.startswith('.')]
    for rel in ['run_detector.py','run_board_r192_fast_acceptance100.py','release_manifest.json','README.md','runtime/board_runtime.py','runtime/hybrid_executor.py',
    'runtime/queue_device.py','runtime_fast/hybrid_executor.py','runtime_fast/fast_topk.py','r192/model/graph.json','r192/model/manifest.json',
    'reports/release_summary.json','reports/acceptance_summary.json','reports/final_review.json','runtime/resident_executor.py']:
        path=folder/rel
        if path.is_file() and path.stat().st_size<100000:
            raw=path.read_bytes();out['source_files'].append({'path':str(path),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.decode('utf-8','replace')})
    for rel in ['runs','reports']:
        directory=folder/rel
        if directory.is_dir():
            out['selected_reports'].append({'directory':str(directory),'items':[{'name':p.name,'directory':p.is_dir(),'bytes':p.stat().st_size if p.is_file() else None} for p in sorted(directory.iterdir())]})
print(json.dumps(out))
