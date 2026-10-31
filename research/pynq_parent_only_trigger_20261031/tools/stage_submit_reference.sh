set -euo pipefail
cd /share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_trigger_20261031
test ! -e reference_job_id.txt
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
root=Path.cwd();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=root/'verification_input_v1.tar.gz'
assert archive.stat().st_size==15114004 and sha(archive)=='17e752aa25fa0043e7b17284dc00a9419878f1d2785bcb33b039bef3e838ac76'
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==len({row.name for row in members})==80
 for row in members:
  rel=PurePosixPath(row.name);assert row.isfile()and not rel.is_absolute()and'..'not in rel.parts
  path=(root/row.name).resolve();assert path.is_relative_to(root)and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(row).read())
p=json.loads((root/'protocol/reference_v1.json').read_text())
assert p['expected_new_Torch_image_forwards']==13 and p['expected_reused_query_features']==12 and p['reused_gallery_vectors']==60
for row in p['files']:assert sha(root/row['file'])==row['sha256']
for name,digest in p['code_sha256'].items():assert sha(root/name)==digest
for model in p['models']:assert sha(Path(model['checkpoint']))==model['checkpoint_sha256']
t=json.loads((root/'tracker_input/protocol.json').read_text())
for row in t['files']:assert sha(root/row['file'])==row['sha256']
import numpy,PIL,torch
print(json.dumps({'status':'ALL_REFERENCE_INPUTS_CODE_CHECKPOINTS_AND_GALLERY_CACHE_VERIFIED_BEFORE_ANY_FORWARD',
 'torch':torch.__version__,'numpy':numpy.__version__,'new_Torch_forwards_planned':13,'reused_gallery_features':60}),flush=True)
PY
bash -n tools/reference.slurm
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
reference_job_id=$(sbatch --parsable tools/reference.slurm)
printf '%s\n' "$reference_job_id" > reference_job_id.txt
printf 'REFERENCE_JOB_ID=%s\n' "$reference_job_id"
