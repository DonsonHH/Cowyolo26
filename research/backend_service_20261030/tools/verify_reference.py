from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import json,tarfile,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=load(ROOT/'evidence/reference_transfer.json');archive=ROOT/'reference_delivery_v1.tar.gz';assert sha(archive)==m['sha256'] and archive.stat().st_size==m['bytes']
out=ROOT/'reference_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==m['members']
 for member in members:
  name=PurePosixPath(member.name);assert member.isfile() and not name.is_absolute() and '..' not in name.parts
  f=out.joinpath(*name.parts).resolve();assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(member).read())
for row in load(out/'reference_manifest.json'):
 f=out/row['file'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
assert sha(out/'tools/reference_encoder.py')==sha(ROOT/'tools/reference_encoder.py')
assert sha(out/'protocol/reference_v1.json')==sha(ROOT/'protocol/reference_v1.json')
p=load(ROOT/'protocol/reference_v1.json');s=load(out/'results/reference/summary.json');checks=load(out/'results/reference/query_checks.json');gchecks=load(out/'results/reference/gallery_checks.json');ret=load(out/'results/reference/retrieval_checks.json')
assert s['status']=='ALL_ACTUAL_PHOTOS_AND30_GALLERY_TORCH_REFERENCE_PASS_FROZEN_NUMERIC_AND_RETRIEVAL_GATES' and s['job_id'] in (ROOT/'evidence/reference_submit.txt').read_text(encoding='utf-8').splitlines()
assert s['query_Torch_forwards']==len(checks)==p['query_count'] and s['gallery_Torch_forwards']==len(gchecks)==30 and len(ret)==2*len(checks)
rows=load(ROOT/'reference_payload/input/jobs.json');labels=p['registered_IDs'];galleryrows=load(ROOT.parent/'pynq_identity_ncnn_20261029/input/images.json')['new_gallery']
with np.load(out/'results/reference/all_reference_features.npz') as ar:
 for index,(r,c) in enumerate(zip(rows,checks)):
  error=float(np.max(np.abs(ar['query_Torch'][index]-ar['query_actual_ARM'][index])));cosine=1-float(ar['query_Torch'][index].astype(float)@ar['query_actual_ARM'][index].astype(float))
  assert error==c['maximum_normalized_feature_difference'] and cosine==c['one_minus_cosine']
  assert error<=p['maximum_normalized_feature_absolute_error'] and cosine<=p['maximum_1_minus_cosine_error'] and c['maximum_input_absolute_error']<=p['maximum_input_absolute_error']
  for name,key in [('same_actual_board_gallery','gallery_actual_ARM'),('fresh_Torch_gallery','gallery_Torch')]:
   dots=ar['query_Torch'][index].astype(float)@ar[key].astype(float).T;scores=np.asarray([max(dots[i] for i,g in enumerate(galleryrows) if g['identity']==label) for label in labels]);winner=int(np.argmax(scores));accepted=bool(scores[winner]>=p['fixed_threshold'])
   record=next(x for x in ret if x['query_index']==index and x['gallery']==name)
   assert labels[winner]==record['predicted_id']==r['predicted_id'] and accepted==record['accepted']==r['accepted']
 for index,c in enumerate(gchecks):
  error=float(np.max(np.abs(ar['gallery_Torch'][index]-ar['gallery_actual_ARM'][index])));assert error==c['maximum_normalized_feature_difference'] and error<=p['maximum_normalized_feature_absolute_error']
assert s['maximum_input_error']==max(c['maximum_input_absolute_error'] for c in checks)==0.
assert s['maximum_query_normalized_error']==max(c['maximum_normalized_feature_difference'] for c in checks)
assert s['maximum_gallery_normalized_error']==max(c['maximum_normalized_feature_difference'] for c in gchecks)
result={'status':'REFERENCE_ARCHIVE_ALL_ACTUAL_QUERIES_AND_GALLERY_SEPARATELY_CHECKED','created_UTC':datetime.now(timezone.utc).isoformat(),**s,
 'verification_status':'REFERENCE_ARTIFACTS_AND_SCORES_SEPARATELY_CHECKED','archive_sha256':m['sha256'],'archive_members':m['members'],'source_input_tensors_exact':True,'whole_goal_complete':False}
f=ROOT/'results/reference_independent_verification.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
