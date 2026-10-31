from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
old=PROJECT/'pynq_identity_ncnn_20261029/protocol/encoder_v1.json';p=json.loads(old.read_text(encoding='utf-8'))
q={'status':'FROZEN_BEFORE_NEW_PHOTO_ENCODER_REFERENCE','created_UTC':datetime.now(timezone.utc).isoformat(),
 'checkpoint':p['encoder_condition']['checkpoint'],'checkpoint_sha256':p['encoder_condition']['checkpoint_sha256'],
 'registered_IDs':p['registered_IDs'],'fixed_threshold':p['fixed_threshold'],
 'maximum_input_absolute_error':1e-6,'maximum_normalized_feature_absolute_error':p['max_normalized_embedding_absolute_error'],
 'maximum_1_minus_cosine_error':p['maximum_1_minus_cosine_error'],'numeric_gate_source_sha256':sha(old),
 'training_primitives_sha256':sha(PROJECT/'pynq_identity_ncnn_20261029/input/training_primitives.py'),
 'all_actual_queries_including_repeats':True,'gallery_Torch_forwards':30,'score_or_threshold_tuning':False,'whole_goal_complete':False}
f=ROOT/'protocol/reference_design_v1.json';assert not f.exists();f.write_text(json.dumps(q,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'frozen_reference_numeric_gates':True,'normalized_error_limit':q['maximum_normalized_feature_absolute_error']}))
