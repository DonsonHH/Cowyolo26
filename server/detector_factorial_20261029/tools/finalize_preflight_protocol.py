from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'tools/preflight.py';target=ROOT/'tools/preflight_v2.py';assert not target.exists()
text=source.read_text().replace('for side in [16,32]:','for side in [16,32,64,128]:')
text=text.replace("ROOT/'protocol/training_v3.json'","ROOT/'protocol/training_v4.json'")
text=text.replace("assert sum(t.rotation_counts.values())==(64 if rotate else 0) and t.rotation_label_rows>0 if rotate else sum(t.rotation_counts.values())==0",
                  "assert sum(t.rotation_counts.values())==(64 if rotate else 0)\n        if rotate:assert t.rotation_label_rows>0")
target.write_text(text,newline='\n')
old=ROOT/'protocol/training_v3.json';p=json.loads(old.read_text());p['version']=4;p['created_UTC']=datetime.now(timezone.utc).isoformat()
p['supersedes_unexecuted_v3_sha256']=sha(old);p['prefight_correction_before_remote_staging']='Fourpower-of-twosides16/32/64/128xCPU/CUDAx6schedules=48;v3codehad24casesbutexpected48;noexecutionyet.'
p['implementation_sha256'].pop('preflight.py');p['implementation_sha256']['preflight_v2.py']=sha(target)
file=ROOT/'protocol/training_v4.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
slurm=ROOT/'tools/preflight_v2.slurm';assert not slurm.exists();slurm.write_text((ROOT/'tools/preflight.slurm').read_text().replace('tools/preflight.py','tools/preflight_v2.py'),newline='\n')
print(json.dumps({'protocol_sha256':sha(file),'preflight_sha256':sha(target),'oracle_cases':48,'remote_new_execution_count':0}))
