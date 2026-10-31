from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from collections import defaultdict
import hashlib,json,tarfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
def load(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

transfer=load(ROOT/'evidence/result_transfer.json');archive=ROOT/'new_encoder_ncnn_delivery_v1.tar.gz'
assert archive.stat().st_size==transfer['bytes']==20140230 and sha(archive)==transfer['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive)as tar:
 members=tar.getmembers();assert len(members)==transfer['members']==33
 for member in members:
  rel=PurePosixPath(member.name);assert member.isfile()and not rel.is_absolute()and'..'not in rel.parts
  path=(out/member.name).resolve();assert path.is_relative_to(out.resolve())and not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
for row in load(out/'result_manifest.json'):assert sha(out/row['file'])==row['sha256']
assert(out/'protocol/run_v1.json').read_bytes()==(ROOT/'protocol/run_v1.json').read_bytes()
plan=load(ROOT/'protocol/run_v1.json');summary=load(out/'results/export/summary.json');rows=load(out/'results/export/input_and_numeric_rows.json')
assert summary['status']=='NEW_DOMAIN_ENCODER_FP32_NCNN630_IMAGE_PARITY_AND1260_DEVELOPMENT_DECISIONS_PASS'
assert summary['actual_trace_Python_forward_calls']==1 and summary['measured_Torch_image_forwards']==summary['measured_NCNN_image_forwards']==630
with np.load(out/'results/export/all_features.npz')as archive:arrays={key:archive[key].copy()for key in archive.files}
assert set(arrays)=={'Torch_raw','NCNN_raw','Torch_normalized','NCNN_normalized'}
for key,array in arrays.items():assert array.shape==(630,576)and array.dtype==np.float32 and np.isfinite(array).all()
for backend in['Torch','NCNN']:
 values=arrays[backend+'_raw'].astype(float);normalized=values/np.sqrt(np.sum(values**2,axis=1))[:,None]
 assert np.max(np.abs(normalized-arrays[backend+'_normalized']))<1e-7
errors=np.max(np.abs(arrays['Torch_normalized']-arrays['NCNN_normalized']),axis=1)
assert float(errors.max())==summary['maximum_normalized_NCNN_vs_Torch_error']and float(errors.max())<.0001
groups=defaultdict(list)
for index,row in enumerate(plan['images']):groups[row['group']].append(index)
parity=load(out/'results/export/development_retrieval_parity.json');calibration=load(out/'results/export/calibration_endpoint_differences.json');checks=0
for case in parity+calibration:
 scope=case['scope'];group='calibration'if scope=='calibration'else'retention'if scope=='retention'else'evaluation'
 ids=plan['eval_registered_IDs']
 allowed=ids[:20]if scope=='fold0'else ids[20:]if scope=='fold1'else ids if scope=='full40'else None
 gi=[index for index in groups[group]if plan['images'][index]['purpose']=='gallery'and(allowed is None or plan['images'][index]['identity']in allowed)]
 labels=sorted({plan['images'][index]['identity']for index in gi});predictions={};scores={}
 for backend in['Torch','NCNN']:
  values={label:max(float(np.dot(arrays[backend+'_normalized'][case['image_index']].astype(float),arrays[backend+'_normalized'][index].astype(float)))for index in gi if plan['images'][index]['identity']==label)for label in labels}
  winner=sorted(values,key=lambda label:(-values[label],label))[0];tau=plan['new_Cows_threshold']if case['policy']=='Cows_calibrated'else plan['original_MultiCam_threshold']
  assert case[backend+'_Top1']==winner and case[backend+'_accepted']==(values[winner]>=tau);predictions[backend]=(winner,values[winner]>=tau);scores[backend]=values
 assert case['same_Top1_and_accept']==(predictions['Torch']==predictions['NCNN'])
 difference=max(abs(scores['Torch'][label]-scores['NCNN'][label])for label in labels);assert abs(difference-case['maximum_registered_score_difference'])<2e-15;checks+=1
assert len(parity)==1260 and all(row['same_Top1_and_accept']for row in parity)
assert len(calibration)==240 and sum(not row['same_Top1_and_accept']for row in calibration)==1
export=out/'results/export';assert sha(export/'encoder.ncnn.param')==summary['NCNN_param_sha256']and sha(export/'encoder.ncnn.bin')==summary['NCNN_bin_sha256']
result={'status':'FULL_NCNN_EXPORT630_FEATURE_PAIRS1260_DEV_AND240_CAL_ENDPOINT_DECISIONS_INDEPENDENTLY_RECOMPUTED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'image_pairs':630,'measured_Torch_forwards':630,'measured_NCNN_forwards':630,
        'actual_Python_trace_forwards':1,'converter_internal_probes_unknown_additional':True,
        'maximum_normalized_NCNN_Torch_error':float(errors.max()),'development_decisions_checked':1260,'development_differences':0,
        'calibration_endpoint_decisions_checked':240,'calibration_endpoint_differences':1,
        'original_archive_bytes':transfer['bytes'],'original_manifest_files':32,'new_model_forwards_by_verification':0,'whole_goal_complete':False}
(ROOT/'results').mkdir(exist_ok=True);p=ROOT/'results/independent_verification.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
