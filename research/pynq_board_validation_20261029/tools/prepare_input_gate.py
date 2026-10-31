from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p={'status':'FROZEN_BEFORE_ACTUAL_BOARD_INPUT_PIXEL_OR_TIMING_PROBE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'board_profile_verification_sha256':sha(ROOT/'results/independent_profile_verification.json'),
 'source_photos':12,'sizes':[192,256,320],'rules':['np_rot90_copy_native_baseline','cv2_rotate_native','cv2_resize_before_rotate'],
 'pixel_gate':'Nativecv2rotateexacttobaselineforall12;resizebeforerotatecomparedwithactualbaselineletterboxforall36;strictbyteequalityrequiredforadoption.',
 'timing_repeats_each_photo_and_rule':3,'image_read_separate':True,'firstimagewarmup_per_rule':1,
 'reference_native_rgb_pixels_saved_and_hashed':True,'candidate_NN_input_arrays_saved_for_independent_gate':True,
 'if_resize_first_not_pixel_exact':'Retainnegativecase;donotuseassameinputlatencyreplacement.',
 'network_forwards':0,'foreground_background_joint_5FPS_proven':False,'whole_goal_complete':False}
target=ROOT/'protocol/input_gate_v1.json';assert not target.exists();target.write_text(json.dumps(p,indent=2)+'\n')
print(sha(target))
