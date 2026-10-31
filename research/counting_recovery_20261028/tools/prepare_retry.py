from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
p=json.loads((ROOT/'protocol/recovery_v1.json').read_text())
assert p['tracker']=='samebuiltinbytetrack.yaml'
p['tracker']='bytetrack.yaml'
p['implementation_correction']={'previous_protocol':'recovery_v1.json','reason':'Use actualinstalledtracker filename instead ofdescriptivetext. No model/threshold/crop/countingparameter change.'}
target=ROOT/'protocol/recovery_v2.json';assert not target.exists();target.write_text(json.dumps(p,indent=2),encoding='utf-8')
source=ROOT/'tools/replay.py';text=source.read_text(encoding='utf-8')
text=text.replace('protocol/recovery_v1.json','protocol/recovery_v2.json').replace("ROOT/'results/replay'","ROOT/'results/replay_v2'")
target=ROOT/'tools/replay_v2.py';assert not target.exists();target.write_text(text,encoding='utf-8')
print(json.dumps({'protocol_sha256':hashlib.sha256((ROOT/'protocol/recovery_v2.json').read_bytes()).hexdigest(),
    'code_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'old_outputs_preserved':True}))
