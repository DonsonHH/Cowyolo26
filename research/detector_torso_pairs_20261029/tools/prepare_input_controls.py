from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((ROOT/'protocol/pairs_v1.json').read_text())
configs=[{'orientation':o,'imgsz':size,'rect':rect,'repeat':False}
         for o in ['clockwise90','original'] for size in [640,320] for rect in [True,False]]
configs.append({'orientation':'clockwise90','imgsz':640,'rect':True,'repeat':True})
probe={'status':'ADAPTIVE_INPUT_FACTORIAL_FROZEN_AFTER_UNEXPECTED_MAIN_MATCH_COUNTS','created_UTC':datetime.now(timezone.utc).isoformat(),
'reason':'Main640rectangularCW90:seed26matched592/1864,seed27505,seed28226;checkinversecoordinatesandinputsize/paddingbeforetraininglocalizer.',
'main_protocol_sha256':sha(ROOT/'protocol/pairs_v1.json'),'main_job_id':'130498','main_job_terminal':'COMPLETED0:0',
'main_case_selection_sha256':sha(ROOT/'evidence/main_cases_before_input_controls.json'),
'models':p['models'],'sample_names':p['fixed_validation_sample_names'],'sample_selection':'Same8hashrankedbeforemainmodelpredictions;nofailurebasedreplacement.',
'configurations':configs,'actual_image_forwards_expected':4*8*9,'new_training_updates':0,
'coordinate_control':'Compareallreference-predictionAABB_IoUsinrotatedframeandrestorednativeframe;mustagree<=1e-10.',
'baseline_repeat':'FirstCW640rectTrueandlastrepeatmustreproducecachedmain8sampleboxes/confidenceswithin1e-4,samecount.',
'previous320comparison':'Compareoriginal/CW320rectFalseagainstoldfrozen320squarecachedpredictionsatconfidence>=.2;batch1vs16numericaldifferencesreported.',
'global_pipeline_changes_allowed':False,'identity_labels_generated':False,'whole_goal_complete':False}
out=ROOT/'protocol/input_controls_v1.json';assert not out.exists();out.write_text(json.dumps(probe,indent=2)+'\n')
print(json.dumps({'protocol_sha256':sha(out),'cases':len(configs),'models':4,'images_each':8,'forwards':288}))
