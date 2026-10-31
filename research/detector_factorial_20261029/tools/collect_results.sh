set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130518,130542,130544 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('detector_factorial_20261029').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for job in ['130542','130544']:
    state=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),(job,state)
freeze=json.loads((root/'results/all_checkpoints_frozen.json').read_text());summary=json.loads((root/'results/evaluation/summary.json').read_text())
assert len(freeze['conditions'])==15 and freeze['total_formal_optimizer_updates']==18375
assert summary['actual_detector_source_image_forwards']==summary['predictor_hook_image_forwards']==63375 and summary['new_counter_paths']==90
files=[f for folder in ['input','protocol','tools','results','logs'] for f in sorted((root/folder).rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
manifest=root/'assembly_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'relative_file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=root.parent/'detector_factorial_20261029_results.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
record={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
file=root.parent/'detector_factorial_20261029_transfer.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
for row in summary['validation_metrics']:print('VAL',row['condition'],row['matched'],row['unmatched_reference'],row['unmatched_prediction'])
for row in summary['video_metrics']:
    if row['counter']=='handoff_events':print('COUNT',row['scene'],row['condition'],row['sample_stride'],row['down'],row['up'],
        [row['formal_event_metrics'][k] for k in ['TP','FP','FN']] if row['formal_event_metrics'] else None)
PY
