from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
archive=ROOT/'next_native_probes_delivery.tar.gz';assert archive.stat().st_size==2641202 and sha(archive)=='3f420e10762bc01b4de85ac335c7867c551e81dd42bcf3b912206fc641b6a2b4'
out=ROOT/'next_native_probes_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as t:
    for m in t.getmembers():
        n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
    t.extractall(out,filter='data')
folder=out/'results/next_native_probes';s=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'input/next_file_probes/manifest.json').read_text(encoding='utf-8'))
assert s['protocol_sha256']==manifest['protocol_sha256']==sha(ROOT/'protocol/next_file_probe_v1.json')
assert sha(ROOT/'next_probes_input.tar')==s['input_archive_sha256']
assert s['HTTP_bytes']==manifest['successful_HTTP_bytes']==88080396
images=0
for row in manifest['files']:
    for r in row['range_reads']:
        assert sha(ROOT/r['file'])==r['sha256'] and (ROOT/r['file']).stat().st_size==r['bytes']
for row in s['probes']:
    assert sha(folder/row['log'])==row['log_sha256']
    if row['native_still_decoded']:
        assert sha(folder/row['file'])==row['image_sha256']
        with Image.open(folder/row['file']) as im:im.load();assert im.size==(1280,720)
        images+=1
assert images==s['decoded_stills']==11 and len(s['probes'])==18
with Image.open(folder/'six_files_native_fraction_overview.jpg') as im:im.load();assert im.size==(1920,2520)
result={'status':'SIX_FILE_NATIVE_PROBES_HASHES_AND_ELEVEN_IMAGES_VERIFIED','attempts':18,'decoded':11,
        'nondecoded_probes_do_not_imply_empty_scene':True,'HTTP_bytes':88080396,'whole_source_validation':False,
        'new_model_predictions':0,'visual_review_pending':True,'whole_goal_complete':False}
target=ROOT/'results/next_probe_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
