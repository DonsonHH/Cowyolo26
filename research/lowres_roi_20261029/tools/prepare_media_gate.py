from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
p={'created_UTC':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_BEFORE_ROI_RESULTS_READ',
'video_layout':'Oneoriginalsourcecomparisonwith3sizerows192/256/320andfull/ROIcolumns;seed26fixedasprevioushuman12acceptedcountingmodel,notselectedbynewROIscore.',
'models_not_in_primary_movie':'All4modelsremainin72pairtablesandsciencefigure;notchosenoutofnegativecaseevaluation.',
'preview_source_anchors':[8995,9345,9790,10830],'movie_export_frame0_inclusive':[8912,10873],'render_fps':25,'network_sample_Hz':5,
'pixel_preprocess_gate':{'maximum_float32_absolute_delta':1.2e-7,'recover_float_input_times255_rounded_matches_independent_uint8_exact':True,
'fixed_native_and_crop_RGB_pixel_hashes_must_match':True,'actual96_anchor_tensor_hashes_across4models_must_match':True},
'no_new_cropping_thresholds_or_models':True,'whole_goal_complete':False}
f=ROOT/'protocol/media_and_pixel_v1.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n');print(hashlib.sha256(f.read_bytes()).hexdigest())
