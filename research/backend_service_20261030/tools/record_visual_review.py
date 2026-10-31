from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=load(ROOT/'results/actual_photo_manifest.json');assert m['actual_photos']==39 and len(m['files'])==4
for row in m['files']:assert sha(row['file'])==row['sha256']
record={'status':'ALL4_RECOVERED_PIXEL_BOUND_CONTACT_SHEETS39_ACTUAL_CAPTURE_PIXELS_VIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'actually_viewed':True,'sheets':4,'panels':39,'reviewer':'assistant_visual_self_review_not_independent_human',
 'PNG_files_are_reconstructions_bound_by_onboard_decoded_RGB_hash':True,
 'files':[{'file':r['file'],'sha256':r['sha256'],'actually_viewed':True} for r in m['files']],
 'observations':['All39 photos viewed:10 idle,9 first parallel,10 second parallel,10 idle. No empty placeholder counted.',
 'First parallel run lacks the spotted long white-body event visible around9265 in the other groups; treat this as development visual comparison, not independent identity GT.',
 'White entry cow remains overexposed, and neighboring bodies remain in several dark-body crops.',
 'f9790 query is accepted in both idle groups and first parallel group; second parallel crop at9790 has lower score and is rejected.',
 'All3 accepts are same f9790 image repeated; no claim of3 different recovered cows.',
 'Four literal event-key pair records and31 unmatched records remain; temporary IDs are not permanent cow identities.'],
 'new_identity_accuracy_proven':False,'selection_or_numeric_rules_changed_after_view':False,'whole_goal_complete':False}
f=ROOT/'results/visual_review.json';assert not f.exists();f.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8');print(json.dumps({'panels_viewed':39,'reconstructed_pixels_hash_bound':True}))
