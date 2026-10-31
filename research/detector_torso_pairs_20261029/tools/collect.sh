set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
for job in 130498 130499 130500; do
    test "$(sacct -j "$job" --noheader --format=State -P | head -n1)" = COMPLETED
done
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/detector_torso_pairs_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((root/'results/pairs/summary.json').read_text());controls=json.loads((root/'results/input_controls/summary.json').read_text())
assert summary['detector_actual_image_forwards']==13093 and controls['actual_source_image_forwards']==288
files=[p for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest=[{'relative_file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
m=root/'results/assembly_manifest.json';assert not m.exists();m.write_text(json.dumps(manifest,indent=2)+'\n')
archive=root.parent/'detector_torso_pairs_20261029_results.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for p in [*files,m]:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
record={'status':'COMPLETED_MAIN_INPUT_CONTROL_AND_PLOT_COLLECTION','archive':str(archive),'bytes':archive.stat().st_size,
'sha256':sha(archive),'members':len(files)+1,'files_bound_by_manifest':len(files)}
p=root.parent/'detector_torso_pairs_20261029_transfer.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record))
PY
