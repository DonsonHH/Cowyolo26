set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130559 --format=JobID,JobName,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('factorial_lane_crop_20261029').resolve()
state=subprocess.check_output(['sacct','-j','130559','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),state
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((root/'results/roi/summary.json').read_text())
assert summary['actual_detector_source_image_forwards']==summary['active_predictor_inference_image_calls']==39810
assert summary['new_crop_counter_paths']==90 and summary['NN_input_anchor_hash_rows']==120 and summary['unique_NN_input_arrays']==24
files=[p for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest=root/'assembly_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'relative_file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root.parent/'factorial_lane_crop_20261029_results.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in [*files,manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
record={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
file=root.parent/'factorial_lane_crop_20261029_transfer.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
for row in summary['paired_full_vs_roi']:
    if row['counter']=='handoff_events':print('PAIRED',row['scene'],row['condition'],row['sample_stride'],row['full_down'],row['crop_down'],row['full_TP_FP_FN'],row['crop_TP_FP_FN'])
PY
