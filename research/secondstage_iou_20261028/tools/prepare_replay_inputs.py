from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=ROOT/'protocol/secondstage_v1.json';files=[]
for seed in [26,27,28]:
    folder=PROJECT/f'confirmation_handoff_20261028/delivery/results/replay_v2/seed{seed}'
    files.append({'seed':seed,'files':[{'name':name,'sha256':sha(folder/name),'bytes':(folder/name).stat().st_size}
                 for name in ['handoff_events.json','observations.json','summary.json']]})
result={'protocol_sha256':sha(p),'prior_handoff_files':files,'additional_binding_only_rules_unchanged':True}
target=ROOT/'protocol/input_binding.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'input_binding_sha256':sha(target)}))
