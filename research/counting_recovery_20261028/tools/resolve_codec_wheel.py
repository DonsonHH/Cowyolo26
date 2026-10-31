from pathlib import Path
import json,urllib.request
ROOT=Path(__file__).resolve().parents[1]
with urllib.request.urlopen('https://pypi.org/pypi/imageio-ffmpeg/0.6.0/json',timeout=20) as response:d=json.load(response)
values=[r for r in d['urls'] if 'manylinux' in r['filename'] and 'x86_64' in r['filename']]
assert len(values)==1
item=values[0];record={k:item[k] for k in ['url','filename','size','digests']}
path=ROOT/'results/codec_wheel_official_metadata.json';assert not path.exists();path.write_text(json.dumps(record,indent=2))
script='''set -euo pipefail
/share/home/renly/projects/idcoo_research_20261026/env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,urllib.request,zipfile
root=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028')
record=RECORD
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
'''.replace('RECORD',repr(record))
(ROOT/'tools/stage_codec_direct.sh').write_text(script,encoding='utf-8')
print(json.dumps(record))
