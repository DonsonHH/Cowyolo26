from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=load(ROOT/'evidence/numeric_transfer.json');a=ROOT/'numeric_delivery.tar.gz';assert sha(a)==m['sha256'] and a.stat().st_size==m['bytes']
out=ROOT/'numeric_delivery';out.mkdir(exist_ok=False)
with tarfile.open(a) as t:
 assert len(t.getmembers())==m['members']
 for member in t.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  p=(out/member.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t.extractfile(member).read())
for row in load(out/'numeric_manifest.json'):assert sha(out/row['file'])==row['sha256'] and (out/row['file']).stat().st_size==row['bytes']
assert sha(out/'protocol/ordered_float_reference_v2.json')==sha(ROOT/'protocol/ordered_float_reference_v2.json')
s=load(out/'results/ordered_reference/summary.json');assert s['protocol_sha256']==sha(ROOT/'protocol/ordered_float_reference_v2.json') and s['all24_ordered_raw_bytes_exact']
checks=[]
for row in s['rows']:
 file=out/row['file'];assert sha(file)==row['sha256']
 with np.load(file) as ar:ordered=ar['ordered_reference'];native=ar['prior_native'];original=ar['original_numpy_reference']
 q=PROJECT/'pynq_rot192_compile_20261029/delivery/results/qualification' if row['size']==192 else ROOT/'delivery'/('s'+str(row['size']))/'results/qualification'
 with np.load(q/('parity_train_'+str(row['index'])+'.npz')) as ar:assert ar['native_integer_raw'].tobytes()==native.tobytes() and ar['reference_integer_raw'].tobytes()==original.tobytes()
 assert ordered.shape==native.shape==(1,300,6) and ordered.tobytes()==native.tobytes()
 assert row['ordered_full_raw_bytes_exact_to_prior_native'] and row['passes_original_value_thresholds']
 assert row['original_numpy_full_raw_bytes_exact_to_prior_native']==(original.tobytes()==native.tobytes())
 checks.append({'size':row['size'],'index':row['index'],'ordered_raw_byte_exact':True,'original_numpy_raw_byte_exact':row['original_numpy_full_raw_bytes_exact_to_prior_native']})
assert len(checks)==24 and sum(r['original_numpy_raw_byte_exact'] for r in checks)==23
c=load(out/'results/probe320_causal/summary.json');assert c['full_reference_matches_native_after_one_boundary_intervention'] and c['original_reference_vs_native_complete_raw_gate_passes'] is False
with np.load(out/'results/probe320_causal/causal_arrays.npz') as ar:
 assert ar['reference_with_one_native_INT8_boundary'].tobytes()==ar['native'].tobytes() and ar['original_reference'].tobytes()!=ar['native'].tobytes()
 assert np.flatnonzero(ar['reference_boundary_INT8'].reshape(-1)!=ar['native_boundary_INT8'].reshape(-1)).tolist()==[7528]
 left=float(ar['reference_boundary_float'].reshape(-1)[7528]);right=float(ar['native_boundary_float'].reshape(-1)[7528])
 assert left==c['boundary']['reference_float'] and right==c['boundary']['native_float']
r={'status':'ALL24_ORDERED_REFERENCE_RAW_ARRAYS_AND_SINGLE_INT8_BOUNDARY_CAUSAL_CONTROL_VERIFIED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'ordered_reference_vectors':24,'ordered_reference_exact':24,'legacy_numpy_reference_exact':23,
 'old320_gate_failure_preserved':True,'first_INT8_boundary_flat_index':7528,'reference_float':left,'native_float':right,
 'original_reference_full_raw_repaired_by_diagnostic_boundary_intervention_only':True,
 'model_weights_calibration_native_engine_and_firmware_changed':False,
 'nonconv_reference_contract_explicitly_changed_from_unspecified_BLAS_order_to_native_scalar_order':True,
 'original_numeric_value_thresholds_relaxed':False,'new_model_forwards_in_this_verifier':0,'whole_goal_complete':False,'checks':checks,
 'numeric_archive_sha256':sha(a)}
file=ROOT/'results/ordered_reference_verification.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='checks'}))
