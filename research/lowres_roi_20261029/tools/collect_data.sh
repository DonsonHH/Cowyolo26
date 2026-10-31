set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130506,130507 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,subprocess
root=Path('/share/home/renly/projects/idcoo_research_20261026/lowres_roi_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for job in ['130506','130507']:
    status=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
    assert status.startswith('COMPLETED|0:0'),(job,status)
summary=json.loads((root/'results/roi/summary.json').read_text())
assert summary['actual_detector_source_image_forwards']==31848 and summary['new_crop_counter_paths']==72
verified=json.loads((root/'results/pixel_independent_verification.json').read_text())
assert verified['raw_frame_crops_verified']==8 and verified['actual_unique_NN_arrays_verified']==24
files=[f for f in sorted(root.rglob('*')) if f.is_file() and '__pycache__' not in f.parts]
manifest=root/'results/assembly_manifest.json';assert not manifest.exists()
manifest.write_text(json.dumps([{'relative_file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=root.parent/'lowres_roi_20261029_data.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
record={'status':'ROI_AND_INDEPENDENT_PIXEL_CHECK_JOBS_COMPLETED_DATA_CLOSED',
        'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
file=root.parent/'lowres_roi_20261029_data_transfer.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
PY
