set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
test "$(sacct -j 130503 --noheader --format=State -P | head -n1)" = COMPLETED
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((root/'results/baseline/summary.json').read_text())
assert s['actual_detector_source_image_forwards']==50700 and s['tracker_updates']==32808
files=[f for f in sorted(root.rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
rows=[{'relative_file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]
m=root/'results/assembly_manifest.json';assert not m.exists();m.write_text(json.dumps(rows,indent=2)+'\n')
out=root.parent/'lowres_baseline_20261029_results.tar.gz';assert not out.exists()
with tarfile.open(out,'w:gz') as tar:
 for f in [*files,m]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
record={'status':'LOWRES_COMPLETE_ALL_VALIDATION_ORIGINAL_AND_RESUMED_TOROS_RESULTS_PRESERVED','archive':str(out),
'bytes':out.stat().st_size,'sha256':sha(out),'members':len(files)+1,'manifest_files':len(rows)}
p=root.parent/'lowres_baseline_20261029_transfer.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
for v in s['validation_metrics']:print('VAL',v['condition'],v['matched'],v['unmatched_reference'],v['unmatched_prediction'])
for v in s['video_metrics']:
 if v['counter']=='handoff_events':
  print('VIDEO',v['scene'],v['condition'],v['nominal_inference_Hz'],'down',v['down'],'up',v['up'],'error',v['absolute_down_total_error'],
        'TPFPFN',[v['formal_event_metrics'][k] for k in ['TP','FP','FN']] if v['formal_event_metrics'] else None)
PY
