from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'admission_delivery.tar.gz';assert p.stat().st_size==28138636 and hashlib.sha256(p.read_bytes()).hexdigest()=='e9ca0b705fa627fd60225b5779a5498fdad19508c163ce8546abee25a55b6d06'
out=ROOT/'admission_delivery';out.mkdir(exist_ok=False)
with tarfile.open(p) as t:
    members=t.getmembers()
    for m in members:
        name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
    t.extractall(out,filter='data')
summary=json.loads((out/'results/admission/summary.json').read_text(encoding='utf-8'));assert summary['frames_total']==637
images=0
for r in summary['videos']:
    for snap in r['snapshots']:
        p=out/snap['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==snap['sha256']
        with Image.open(p) as im:im.load();assert im.size==(1280,720)
        images+=1
    p=out/r['native_proxy'];assert hashlib.sha256(p.read_bytes()).hexdigest()==r['native_proxy_sha256']
assert images==20
result={'status':'ADMISSION_ARCHIVE_AND_TWENTY_NATIVE_IMAGE_DECODES_VERIFIED','archive_bytes':28138636,'files':len(members),'images':images,'videos':4,'native_frames':637,'pixels_visually_reviewed':False}
(ROOT/'evidence/admission_local_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
