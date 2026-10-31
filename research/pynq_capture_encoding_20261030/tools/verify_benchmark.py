from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=load(ROOT/'evidence/benchmark_transfer.json');archive=ROOT/'benchmark_delivery.tar.gz';assert sha(archive)==m['sha256'] and archive.stat().st_size==m['bytes']
out=ROOT/'benchmark_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 assert len(tar.getmembers())==m['members']
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=(out/member.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
for r in load(out/'benchmark_manifest.json'):assert sha(out/r['file'])==r['sha256'] and (out/r['file']).stat().st_size==r['bytes']
assert sha(out/'protocol.json')==sha(ROOT/'protocol/encoding_v1.json')
s=load(out/'encoding_results/summary.json');assert s['status']=='ALL11_PHOTOS_TWO_LOSSLESS_PNG_ENCODINGS_ACTUALLY_MEASURED' and len(s['rows'])==22
statistics=[]
for index in range(11):
 a,b=[next(r for r in s['rows'] if r['photo_index']==index and r['PNG_compress_level']==level) for level in [6,0]]
 with Image.open(out/'encoding_results'/a['output_file']) as im:x=np.asarray(im.convert('RGB'))
 with Image.open(out/'encoding_results'/b['output_file']) as im:y=np.asarray(im.convert('RGB'))
 assert x.shape==y.shape and x.tobytes()==y.tobytes() and hashlib.sha256(x.tobytes()).hexdigest()==a['decoded_RGB_sha256']==b['decoded_RGB_sha256']
for level in [6,0]:
 rows=[r for r in s['rows'] if r['PNG_compress_level']==level]
 statistics.append({'level':level,'images':len(rows),'mean_wall_ms':float(np.mean([r['encode_file_wall_ms'] for r in rows])),
  'mean_CPU_ms':float(np.mean([r['encode_file_CPU_ms'] for r in rows])),'file_bytes':sum(r['output_bytes'] for r in rows)})
result={'status':'ALL22_ACTUAL_BOARD_PNG_WRITES_AND11_PAIRWISE_DECODED_RGB_IMAGES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'statistics':statistics,'pixel_identical_photo_pairs':11,'mean_wall_speed_ratio_level6_vs0':statistics[0]['mean_wall_ms']/statistics[1]['mean_wall_ms'],
 'file_byte_ratio_level0_vs6':statistics[1]['file_bytes']/statistics[0]['file_bytes'],'new_model_forwards':0,
 'microbenchmark_is_not_periodic_pipeline_speed_proof':True,'whole_goal_complete':False,'archive_sha256':sha(archive)}
file=ROOT/'results/encoding_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
