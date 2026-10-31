from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'delivery/results/export_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=load(ROOT/'protocol/encoder_v1.json');s=load(OUT/'summary.json');rows=load(OUT/'vector_manifest.json');groups=load(ROOT/'input/images.json')
assert s['protocol_sha256']==sha(ROOT/'protocol/encoder_v1.json') and s['encoder_checkpoint_sha256']==p['encoder_condition']['checkpoint_sha256']
assert s['real_image_forwards']=={'TorchCPU':132,'ncnnCPU':132} and len(rows)==132
refs={};native={};maxerr=0.;maxprior=0.
with np.load(ROOT/'input/prior_embeddings.npz') as previous:
 for row in rows:
  file=OUT/row['file'];assert sha(file)==row['sha256']
  with np.load(file) as a:
   x=a['input'];r=a['Torch_raw'];n=a['ncnn_raw'];rz=a['Torch_normalized'];nz=a['ncnn_normalized']
   assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_tensor_sha256'] and x.shape==(1,3,224,224)
   assert r.shape==n.shape==rz.shape==nz.shape==(576,) and np.isfinite(n).all()
   rr=r.astype(np.float64)/np.sqrt(np.sum(r.astype(np.float64)**2));nn=n.astype(np.float64)/np.sqrt(np.sum(n.astype(np.float64)**2))
   assert np.max(np.abs(rr-rz))<5e-8 and np.max(np.abs(nn-nz))<5e-8
   error=float(np.max(np.abs(rz-nz)));cosine=float(rz.astype(np.float64)@nz.astype(np.float64))
   assert error==row['max_normalized_difference']<=.0001 and abs(cosine-row['cosine'])<1e-12 and 1-cosine<=.00001
   prior=float(np.max(np.abs(rz-previous[row['group']][row['index']])));assert prior==row['maximum_reference_vs_prior_normalized_error']<=.0002
   maxerr=max(maxerr,error);maxprior=max(maxprior,prior)
   refs.setdefault(row['group'],[]).append(rz);native.setdefault(row['group'],[]).append(nz)
 for k in refs:refs[k]=np.stack(refs[k]);native[k]=np.stack(native[k])
checks=[]
for gallery in ['old_gallery','new_gallery']:
 for queries in ['labelled_query','real_event_query']:
  results=[]
  for features in [refs,native]:
   score=[]
   for query in features[queries]:
    perID={label:max(float(np.dot(query.astype(float),g.astype(float))) for row,g in zip(groups[gallery],features[gallery]) if row['identity']==label) for label in p['registered_IDs']}
    winner=sorted(perID,key=lambda k:(-perID[k],p['registered_IDs'].index(k)))[0]
    score.append((winner,perID[winner]>=p['fixed_threshold']))
   results.append(score)
  assert results[0]==results[1]
  checks.append({'gallery':gallery,'query_group':queries,'images':len(results[0]),'all_rank1_and_acceptance_exact':True})
reuse=load(OUT/'converted_asset_reuse.json')
for row in reuse['assets']:
 assert sha(OUT/row['file'])==row['sha256']==sha(ROOT/'delivery/results/export'/row['file'])
assert maxerr==s['maximum_normalized_embedding_difference'] and maxprior==s['maximum_prior_embedding_difference']
result={'status':'ALL132_SERVER_NCNN_NORMALIZED_FEATURES_AND144_RETRIEVAL_DECISIONS_INDEPENDENTLY_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'vectors':132,'retrieval_decisions':sum(x['images'] for x in checks),
 'maximum_normalized_embedding_difference':maxerr,'maximum_prior_embedding_difference':maxprior,'retrieval_checks':checks,
 'failed_wrapper_assets_preserved_and_reused_byte_exact':True,'new_training_updates':0,'new_model_forwards':0,
 'actual_board_encoder_inference_verified_in_this_record':False,'real_event_permanent_identity_accuracy_proven':False,'whole_goal_complete':False}
file=ROOT/'results/independent_export_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
