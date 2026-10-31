from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];Q=ROOT/'delivery/results/export_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=load(ROOT/'evidence/board_transfer.json');archive=ROOT/'board_delivery.tar.gz';assert sha(archive)==m['sha256'] and archive.stat().st_size==m['bytes']
OUT=ROOT/'board_delivery';OUT.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==m['members']
 for item in members:
  assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  p=(OUT/item.name).resolve();assert p.is_relative_to(OUT.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(item).read())
manifest=load(OUT/'board_manifest.json');assert len(manifest)==m['manifest_files']
for row in manifest:
 p=OUT/row['file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
for a,b in [('vectors_protocol_v3.json','protocol/board_vectors_v3.json'),('ncnn_encoder_v3.py','tools/ncnn_encoder_v3.py'),
 ('board_vectors_v3.py','tools/board_vectors_v3.py'),('build_protocol_v2.json','protocol/board_build_v2.json')]:assert sha(OUT/a)==sha(ROOT/b)
p=load(OUT/'vectors_protocol_v3.json');s=load(OUT/'vectors_results_v3/record.json');terminal=load(OUT/'vectors_results_v3/terminal.json')
assert s['status']==terminal['status']=='ALL132_ACTUAL_ARM_NCNN_VECTORS_PREPROCESS_AND_RETRIEVAL_PASS_FROZEN_GATES'
assert terminal['record_sha256']==sha(OUT/'vectors_results_v3/record.json') and s['protocol_sha256']==sha(OUT/'vectors_protocol_v3.json')
assert s['model_forwards']==terminal['model_forwards']==len(s['rows'])==132 and len(s['warmups'])==2
assert s['torch_imported'] is False and s['PL_actions']==0 and s['library_sha256']==sha(OUT/'libcow_encoder_v2.so')
built=load(OUT/'build_v2_result.json');assert built['bridge_library_sha256']==s['library_sha256'] and built['encoder_checkpoint_sha256']==p['encoder_checkpoint_sha256']
assert 'VFPv4' not in (OUT/'A9_library_attributes_v2.txt').read_text() and 'NCNN_VFPV4:BOOL=OFF' in (OUT/'build_v2/CMakeCache.txt').read_text()
assert 'NCNN_VFPV4:BOOL=ON' in (OUT/'build/CMakeCache.txt').read_text() and load(OUT/'native_crash_diagnostic.json')['returncode']==-4
gate=load(OUT/'vectors_results_v3/preprocessing_gate.json');assert gate['model_forwards']==0 and len(gate['cases'])==132 and all(r['maximum_tensor_difference']==0 and r['passes'] for r in gate['cases'])
rows=load(Q/'vector_manifest.json');assert [r['name'] for r in rows]==[r['name'] for r in s['rows']]
features={};references={};maximum=preprocessmax=0.;cosines=[]
for reference,row in zip(rows,s['rows']):
 with np.load(Q/reference['file']) as a:expected=a['Torch_normalized'];input_tensor=a['input']
 file=OUT/'vectors_results_v3'/row['output_file'];assert sha(file)==row['output_sha256']
 with np.load(file) as a:raw=a['raw'];normalized=a['normalized'];runtime=a['runtime_body_tensor']
 assert raw.shape==normalized.shape==(576,) and np.isfinite(raw).all()
 reconstructed=raw.astype(np.float64)/np.sqrt(np.sum(raw.astype(np.float64)**2));assert np.max(np.abs(reconstructed-normalized))<5e-8
 assert runtime.tobytes()==input_tensor.tobytes() and hashlib.sha256(input_tensor.tobytes()).hexdigest()==row['tensor_sha256']
 error=float(np.max(np.abs(expected-normalized)));cosine=float(expected.astype(np.float64)@normalized.astype(np.float64))
 assert error==row['max_normalized_embedding_difference']<=p['max_normalized_embedding_absolute_error'] and abs(cosine-row['cosine'])<1e-12
 assert 1-cosine<=p['maximum_1_minus_cosine_error'] and row['runtime_Pillow_tensor_max_difference']==0
 maximum=max(maximum,error);cosines.append(cosine)
 references.setdefault(row['group'],[]).append(expected);features.setdefault(row['group'],[]).append(normalized)
for key in features:references[key]=np.stack(references[key]);features[key]=np.stack(features[key])
groups=load(ROOT/'input/images.json');checks=[]
for gallery in ['old_gallery','new_gallery']:
 for querygroup in ['labelled_query','real_event_query']:
  outcomes=[];matrices=[]
  for backend in [references,features]:
   matrix=[]
   for query in backend[querygroup]:
    perID=[max(float(np.dot(query.astype(float),g.astype(float))) for row,g in zip(groups[gallery],backend[gallery]) if row['identity']==label) for label in p['registered_IDs']]
    matrix.append(perID)
   matrix=np.asarray(matrix);matrices.append(matrix)
   outcomes.append([(int(np.argmax(row)),float(np.max(row))>=p['fixed_threshold']) for row in matrix])
  assert outcomes[0]==outcomes[1]
  error=float(np.max(np.abs(matrices[0]-matrices[1])))
  reported=next(r for r in s['retrieval_checks'] if r['gallery']==gallery and r['queries']==querygroup)
  assert abs(error-reported['max_similarity_difference'])<1e-12 and reported['all_top1_and_acceptances_exact']
  checks.append({'gallery':gallery,'query_group':querygroup,'images':len(outcomes[0]),'rank1_and_threshold_decisions_exact':True,'maximum_score_difference':error})
assert maximum==s['max_normalized_embedding_difference']
modeltimes=np.asarray([r['model_ms'] for r in s['rows']]);assert float(modeltimes.mean())==s['mean_model_ms']
old=load(OUT/'vectors_results_v2/record.json');assert old['status']=='FAILED' and old['model_forwards']==4 and len(old['warmups'])==2
result={'status':'ALL132_REAL_ARM_IDENTITY_FEATURES132_PHOTO_INPUT_TENSORS_AND144_RETRIEVAL_DECISIONS_INDEPENDENTLY_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'encoder_checkpoint_sha256':p['encoder_checkpoint_sha256'],
 'bridge_library_sha256':s['library_sha256'],'actual_model_vectors':132,'warmups':2,'prior_failed_model_vectors':4,'prior_failed_warmups':2,
 'all132_runtime_photo_tensor_bytes_exact_to_server':True,'maximum_normalized_feature_difference':maximum,
 'retrieval_decisions':sum(r['images'] for r in checks),'all_retrieval_decisions_exact':True,'retrieval_checks':checks,
 'model_ms':{'mean':float(modeltimes.mean()),'p95':float(np.quantile(modeltimes,.95)),'max':float(modeltimes.max())},
 'CortexA9_no_VFPv4':True,'old_native_instruction_and_preprocessing_failures_preserved':True,
 'global_Pillow_or_numpy_changed':False,'new_training_updates':0,'PL_actions':0,'new_permanent_identity_accuracy_proven':False,
 'whole_goal_complete':False,'archive_sha256':sha(archive),'archive_members':len(members),'manifest_files':len(manifest)}
file=ROOT/'results/independent_board_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
