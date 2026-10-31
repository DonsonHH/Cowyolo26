from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,gzip,hashlib,math
from PIL import Image
from independent_geometry import verify_selection
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=load(ROOT/'protocol/run_v1.json');s=load(ROOT/'results/readonly_pairs.json');manifest=load(ROOT/'results/readonly_visual_manifest.json')
t=json.loads(gzip.decompress(Path(p['local_readonly_source']['trace']).read_bytes()));byframe=defaultdict(list)
for row in t['post_tracker']:byframe[row['frame0']].append(row)
events=[r for r in t['handoff_events'] if 8912<=r['frame0']<=10873];assert events==[r['event'] for r in s['pairs']]
camera=PROJECT/'pynq_periodic_joint_20261030/camera_delivery/highres';candidates=0
for pair in s['pairs']:
 candidates+=verify_selection(pair['selection'],list(range(8915,10874,5)),byframe)
 for kind in ['current','selected']:
  row=pair[kind];c=pair['selection'][kind];f=camera/('f'+str(c['frame0']).zfill(5)+'.jpg');assert sha(f)==row['native_JPEG_sha256']
  x,y,z,w=c['xyxy'];crop=[max(0,math.floor(x-870)),max(0,math.floor(y)),min(1050,math.ceil(z-870)),min(1440,math.ceil(w))]
  with Image.open(f) as im:im.load();expected=im.convert('RGB').crop(crop).transpose(Image.Transpose.ROTATE_270)
  file=ROOT/row['file'];assert sha(file)==row['sha256'] and row['native_crop_xyxy']==crop
  with Image.open(file) as im:im.load();assert im.convert('RGB').tobytes()==expected.tobytes()
for page in manifest['files']:
 assert sha(page['file'])==page['sha256']
 with Image.open(page['file']) as im:im.load();canvas=im.convert('RGB')
 for panel in page['panels']:
  assert sha(panel['file'])==panel['sha256'];x,y,w,h=panel['rect']
  with Image.open(panel['file']) as im:im.load();thumb=im.convert('RGB');thumb.thumbnail((520,160),Image.Resampling.BILINEAR)
  assert thumb.size==(w,h) and thumb.tobytes()==canvas.crop((x,y,x+w,y+h)).tobytes()
summary={'status':'ALL10_DEVELOPMENT_SELECTIONS_AND20_NATIVE_PHOTOS_SEPARATELY_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'events':len(events),'candidate_observations':candidates,'photos':20,'contact_panels_pixel_checked':20,
 'selected_older':sum(x['selection']['selected_age_frames']>0 for x in s['pairs']),
 'edge_margin_increased':sum(x['selection']['selected']['minimum_edge_margin_px']>x['selection']['current']['minimum_edge_margin_px'] for x in s['pairs']),
 'overlap_proxy_decreased':sum(x['selection']['selected']['max_other_box_overlap_fraction']<x['selection']['current']['max_other_box_overlap_fraction'] for x in s['pairs']),
 'visible_box_area_increased':sum(x['selection']['selected']['visible_box_area_px2']>x['selection']['current']['visible_box_area_px2'] for x in s['pairs']),
 'sharpness_proxy_increased':sum(x['selected']['fixed128_laplacian_variance_proxy']>x['current']['fixed128_laplacian_variance_proxy'] for x in s['pairs']),
 'sharpness_proxy_decreased':sum(x['selected']['fixed128_laplacian_variance_proxy']<x['current']['fixed128_laplacian_variance_proxy'] for x in s['pairs']),
 'proxy_metrics_not_visibility_or_identity_truth':True,'new_model_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/readonly_independent_verification.json';assert not f.exists();f.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
review={'status':'BOTH_CONTACT_SHEETS_ALL20_PANELS_ACTUALLY_VIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),'files':[{'file':r['file'],'sha256':r['sha256']} for r in manifest['files']],
 'panels':20,'actually_viewed':True,'reviewer':'assistant_visual_self_review_not_independent_human',
 'observations':['T3 earlier photograph has more border margin; brightness remains saturated.',
 'T5 torso view similar; T6 and T11 unchanged; neighboring body remains in T11 crop.',
 'T8 overlap reduced but another cow still visible; T17 neighbor body remains in both.',
 'T19 earlier crop visibly reduces motion blur around shoulder/back; T21 unchanged.',
 'T31 similar clear torso; T36 earlier torso covers more pattern but neighboring cow remains.'],
 'automatic_identity_accuracy_claim':False,'rule_changed_after_viewing':False}
f=ROOT/'results/readonly_visual_review.json';assert not f.exists();f.write_text(json.dumps(review,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary))
