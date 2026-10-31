set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
mkdir -p "$root/media_runtime_wheels"
PIP_DISABLE_PIP_VERSION_CHECK=1 /share/home/renly/projects/idcoo_research_20261026/env/bin/python -m pip download --no-deps --only-binary=:all: --index-url https://pypi.org/simple --dest "$root/media_runtime_wheels" imageio-ffmpeg==0.6.0
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import zipfile,hashlib,json,os
root=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028')
wheel=next((root/'media_runtime_wheels').glob('imageio_ffmpeg-0.6.0-*.whl'))
with zipfile.ZipFile(wheel) as z:
    names=[n for n in z.namelist() if n.startswith('imageio_ffmpeg/binaries/ffmpeg-') and not n.endswith('/')]
    assert len(names)==1
    path=root/'media_ffmpeg';assert not path.exists()
    path.write_bytes(z.read(names[0]));path.chmod(0o700)
record={'wheel':wheel.name,'wheel_sha256':hashlib.sha256(wheel.read_bytes()).hexdigest(),
 'registry':'https://pypi.org/simple','binary_member':names[0],'binary_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
 'existing_environment_modified':False}
(root/'results/media_runtime_staging.json').write_text(json.dumps(record,indent=2));print(json.dumps(record))
PY
