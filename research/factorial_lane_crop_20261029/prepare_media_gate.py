from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
training=PROJECT/'detector_factorial_20261029';old=PROJECT/'lowres_roi_20261029'
p={'status':'FROZEN_BEFORE_NEW_CROP_RESULTS_READ','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'primary_seed':26,'movie_variants':['plain','rot90'],'sizes':[192,256,320],
 'movie_layout':'Twofixedseed26movies;each3sizerowsxfull/cropcolumns;plain320ishistoricalcontrol,allotherrowsnew15frozenmodels.',
 'all18_numeric_conditions_preserved_including3_historical320plain':True,'movie_scope_frame0_inclusive':[8912,10873],
 'render_fps':25,'held_detector_sample_Hz':5,'dimensions':[1280,1120],'source_anchors':[8995,9345,9790,10830],
 'numerical_figure':'3sizerowsxplain/rot90columns;all3seedsfull/croppaireddowncounts;human12reference;320plainhistoricalcontrolmarked.',
 'baseline_full_results_local':str((training/'delivery/results/evaluation').resolve()),
 'historical_full_results_local':str((PROJECT/'lowres_baseline_20261029/delivery/results/baseline').resolve()),
 'historical_crop_results_local':str((old/'delivery/results/roi').resolve()),
 'FP32_server_sampling_not_PYNQ_throughput':True,'no_count_based_seed_or_movie_selection':True,
 'new_training_updates':0,'board_actions':0,'whole_goal_complete':False}
file=ROOT/'protocol/media_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'media_protocol_sha256':sha(file),'fixed_movies':2,'model_seed_selection_not_based_on_ROI_counts':True}))
