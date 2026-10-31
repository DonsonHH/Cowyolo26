from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];Q=ROOT/'delivery/s320/results/qualification'
rows=[]
for i in range(8):
 with np.load(Q/('parity_train_'+str(i)+'.npz')) as ar:a=ar['reference_integer_raw'][0];b=ar['native_integer_raw'][0]
 same=np.flatnonzero(np.any(a!=b,axis=1));record={'index':i,'differing_query_rows':same.tolist(),'byte_exact':a.tobytes()==b.tobytes(),
  'coordinate_max_error':float(np.max(np.abs(a[:,:4]-b[:,:4]))),'score_max_error':float(np.max(np.abs(a[:,4]-b[:,4]))),
  'reference_detections_conf02':int((a[:,4]>=.2).sum()),'native_detections_conf02':int((b[:,4]>=.2).sum()),
  'conf02_kept_rows_byte_exact':a[a[:,4]>=.2].tobytes()==b[b[:,4]>=.2].tobytes(),
  'maximum_score_of_differing_rows':max([max(float(a[k,4]),float(b[k,4])) for k in same]+[0.]),
  'mismatches':[{'row':int(k),'reference':a[k].tolist(),'native':b[k].tolist()} for k in same[:12]]}
 # Are unmatched rows merely equal-score permutations or genuinely different candidates?
 left=[row.tobytes() for row in a];right=[row.tobytes() for row in b]
 record['whole_raw_row_multiset_equal']=sorted(left)==sorted(right)
 record['reference_rows_not_found_in_native']=[k for k,row in enumerate(left) if row not in set(right)]
 rows.append(record)
r={'status':'FAILED320_RAW_PARITY_DIFFERENCE_LOCALIZED_WITHOUT_NEW_MODEL_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),
 'rows':rows,'strict_full_raw_gate_relaxed':False,'board320_inference_started':False,'whole_goal_complete':False}
file=ROOT/'results/failed320_parity_diagnostic.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps([row for row in rows if not row['byte_exact']]))
