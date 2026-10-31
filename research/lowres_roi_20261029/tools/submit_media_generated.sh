set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile,json,subprocess
project=Path('/share/home/renly/projects/idcoo_research_20261026');root=project/'lowres_roi_20261029'
for job in ['130506','130507']:
    state=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
    assert state.startswith('COMPLETED|0:0'),state
archive=project/'lowres_roi_media_inputs.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()=='34da2850bf43a90d7575849151011a0dfcdb9fc9a2266d1e35d70ecdfe37b9f4'
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        target=(root/item.name).resolve();assert target.is_relative_to(root.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(item).read())
for row in json.loads((root/'input/media_staging_manifest.json').read_text()):
    p=root/row['file'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
print('MEDIA_INPUTS_EXACT; CPU-only allocation on idle4gpu; cu all allocated; no GPU GRES')
PY
sbatch --parsable lowres_roi_20261029/tools/media.slurm
