set -euo pipefail
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,urllib.request,zipfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028')
record={'url': 'https://files.pythonhosted.org/packages/a0/2d/43c8522a2038e9d0e7dbdf3a61195ecc31ca576fb1527a528c877e87d973/imageio_ffmpeg-0.6.0-py3-none-manylinux2014_x86_64.whl', 'filename': 'imageio_ffmpeg-0.6.0-py3-none-manylinux2014_x86_64.whl', 'size': 29498237, 'digests': {'blake2b_256': 'a02d43c8522a2038e9d0e7dbdf3a61195ecc31ca576fb1527a528c877e87d973', 'md5': 'eae7521ec21afc38a16f8d445278e40d', 'sha256': 'c7e46fcec401dd990405049d2e2f475e2b397779df2519b544b8aab515195282'}}
path=root/'media_ffmpeg_direct';assert not path.exists()
with urllib.request.urlopen(record['url'],timeout=20) as response:data=response.read()
assert len(data)==record['size'] and hashlib.sha256(data).hexdigest()==record['digests']['sha256']
wheel=root/record['filename'];assert not wheel.exists();wheel.write_bytes(data)
with zipfile.ZipFile(wheel) as z:
    names=[n for n in z.namelist() if n.startswith('imageio_ffmpeg/binaries/ffmpeg-') and not n.endswith('/')]
    assert len(names)==1
    path.write_bytes(z.read(names[0]));path.chmod(0o700)
record['binary_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
(root/'results/direct_codec_staging.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
PY
