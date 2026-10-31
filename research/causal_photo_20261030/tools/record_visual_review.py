from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/actual_panel_pixel_verification.json');m=load(ROOT/'results/actual_photo_manifest.json');assert v['panels']==39
for row in m['files']:assert sha(row['file'])==row['sha256']
result={'status':'ALL4_ACTUAL_ARM_CONTACT_SHEETS_AND39_PHOTOS_ACTUALLY_VIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actually_viewed':True,'reviewer':'assistant_visual_self_review_not_independent_human','panels':39,'sheets':4,
 'files':[{'file':r['file'],'sha256':r['sha256'],'actually_viewed':True} for r in m['files']],
 'observations':['All accepted and rejected photos viewed, including9-photo second current-frame run; no blank panel counted as a photo.',
 'Earlier T3 photographs show smaller white-body region with more edge clearance; highlights remain saturated.',
 'Dark-body and nearby-cow crops remain mixed; geometric overlap proxy does not remove other animals.',
 'Causal r1 temporary T7/T10 and later temporary numbers differ from current-frame labels; do not use these as permanent identities.',
 'The f9790 spotted torso is the sole accepted candidate in all4 groups; selected frame unchanged there.',
 'Causal choice can change top provisional ID (for example f9880 patterned torso is031); no identity truth to adjudicate.',
 'Exact event-frame+temporary-ID matching yields only7 pair records and25 unmatched condition records; none silently dropped.'],
 'numeric_photo_choice_or_threshold_changed_after_view':False,'identity_accuracy_proven':False,'whole_goal_complete':False}
f=ROOT/'results/actual_visual_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({'panels_actually_viewed':39,'sheets':4}))
