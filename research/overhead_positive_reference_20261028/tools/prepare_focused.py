"""Freeze focused review windows and extraction rules after native overview, before inference."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
visual=ROOT/'evidence/overview_visual_review.json';v=json.loads(visual.read_text(encoding='utf-8'))
assert v['new_model_predictions']==0 and v['reference_total_not_yet_assigned']
rows=[{'name':'group_passage','start_frame0':2375,'end_frame0_exclusive':4375},
      {'name':'late_single','start_frame0':5000,'end_frame0_exclusive':5625},
      {'name':'person_control','start_frame0':9625,'end_frame0_exclusive':10125}]
for r in rows:
    r.update(sample_hz=5,sample_stride=5,contact_stride=25,sample_frames=len(range(r['start_frame0'],r['end_frame0_exclusive'],5)),
             contact_frames=len(range(r['start_frame0'],r['end_frame0_exclusive'],25)))
p={'name':'Prediction-free focused native review for assistant event-reference draft','source_sha256':v['source_sha256'],
   'overview_visual_review_sha256':sha(visual),'source_fps':25,'ROI_native_xyxy':[870,0,1920,1440],
   'gate_y_native':[576,864],'center_ROI_x':[.34,.75],'nominal_gate_y':[.4,.6],
   'sample_hz':5,'contact_hz':1,'windows':rows,'total_sample_frames':sum(r['sample_frames'] for r in rows),
   'total_contact_frames':sum(r['contact_frames'] for r in rows),'native_body_center_manual_annotation_planned':True,
   'reference_authority':'assistant provisional annotation from original pixels, requires independent review',
   'new_models_or_pseudolabels_used':False,'whole_goal_complete':False}
out=ROOT/'protocol/focused_review_v1.json';assert not out.exists();out.write_text(json.dumps(p,indent=2),encoding='utf-8')
print(json.dumps(p))
