from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=load(ROOT/'results/actual_photo_manifest.json');assert m['actual_photos']==40 and len(m['files'])==4
for r in m['files']:assert sha(r['file'])==r['sha256']
record={'status':'ALL4_SERIAL_ASYNC_CONTACT_SHEETS40_ACTUAL_PHOTOS_VIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actually_viewed':True,'sheets':4,'panels':40,'reviewer':'assistant_visual_self_review_not_independent_human',
 'files':[{'file':r['file'],'sha256':r['sha256'],'actually_viewed':True} for r in m['files']],
 'observations':['All10 actual jobs in each of4 runs viewed, including both serial groups with zero accepted candidates.',
 'White cow at f8980 remains overexposed; higher frame acquisition throughput did not fix that exposure.',
 'Neighboring bodies remain inside several crops around9340 and9470; geometry ranking is not segmentation.',
 'f9790 spotted torso is accepted only in the2 async groups; serial crops of9790 and9795 are rejected.',
 'The two accepted photographs are repeated same-source views, not2 independently verified cows.',
 'Different temporary IDs, source-frame timing, and crop boundaries remain;6 literal event-key pairs and28 unmatched condition records are all retained.'],
 'identity_accuracy_proven':False,'numeric_or_selection_rules_changed_after_view':False,'whole_goal_complete':False}
f=ROOT/'results/visual_review.json';assert not f.exists();f.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({'photos_actually_viewed':40,'sheets':4}))
