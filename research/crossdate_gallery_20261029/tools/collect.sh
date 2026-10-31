set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
test "$(sacct -j 130423 --noheader --format=State -P | head -n1)" = COMPLETED
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((root/'results/study_v2/summary.json').read_text())
assert summary['actual_image_forwards']==660 and summary['retrieval_decisions']==720 and summary['Slurm_JOB_ID']=='130423'
paths=[p for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest=[{'relative_file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
mp=root/'results/assembly_manifest.json';assert not mp.exists();mp.write_text(json.dumps(manifest,indent=2)+'\n')
archive=root.parent/'crossdate_gallery_20261029_results.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for p in [*paths,mp]:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
metadata={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(paths)+1,'files_bound_by_manifest':len(manifest),'status':'COMPLETED_RESULTS_AND_FAILED_ATTEMPT_PRESERVED'}
meta=root.parent/'crossdate_gallery_20261029_results_transfer.json';assert not meta.exists();meta.write_text(json.dumps(metadata,indent=2)+'\n')
print(json.dumps(metadata))
PY
