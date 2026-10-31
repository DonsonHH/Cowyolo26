from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];q=ROOT/'delivery/results/qualification';board=ROOT/'board_delivery/results'
rows=[]
for i in range(8):
    with np.load(q/('parity_train_'+str(i)+'.npz')) as ar:ref=ar['reference_integer_raw'];native=ar['native_integer_raw']
    actual=np.load(board/('vector_'+str(i)+'_raw.npy'));assert ref.dtype==native.dtype==actual.dtype==np.float32
    assert ref.tobytes()==native.tobytes()==actual.tobytes()
    rows.append({'index':i,'bytes':actual.nbytes,'CPU_reference_native_and_board_bytes_exact':True,'raw_sha256':hashlib.sha256(actual.tobytes()).hexdigest()})
result={'status':'ALL8_CPU_REFERENCE_NATIVE_AND_REAL_BOARD_RAW_BYTES_EXACT_INCLUDING_SIGNED_ZERO',
        'created_host_UTC':datetime.now(timezone.utc).isoformat(),'arrays':rows,'new_network_forwards':0,'whole_goal_complete':False}
file=ROOT/'results/strict_raw_bytes_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(result['status'])
