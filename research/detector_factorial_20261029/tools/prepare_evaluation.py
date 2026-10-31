from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=PROJECT/'lowres_baseline_20261029';p=json.loads((base/'protocol/baseline_v2_path_fix.json').read_text());training=json.loads((ROOT/'protocol/training_v4.json').read_text())
files={'validation_images.json':base/'input/validation_images.json','zone_counter.py':base/'input/zone_counter.py',
 'confirmation_counter.py':base/'input/confirmation_counter.py','event_metrics.py':base/'input/event_metrics.py'}
for name,src in files.items():dest=ROOT/'input'/name;assert not dest.exists();shutil.copyfile(src,dest)
for name in ['geometry.py']:dest=ROOT/'tools'/name;assert not dest.exists();shutil.copyfile(base/'tools'/name,dest)
conditions=[{'condition':c['condition_id'],'model':c['condition_id'],'seed':c['seed'],'input_size':c['imgsz'],
             'right_angle':c['right_angle'],'new_training':True} for c in training['new_conditions']]
controls=[c for c in p['conditions'] if c['model']=='official' or c['input_size']==320 and c['model'].startswith('seed')]
assert len(conditions)==15 and len(controls)==6
protocol={'status':'FROZEN_BEFORE_ALL_NEW_WEIGHT_FREEZE_AND_BEFORE_NEW_MODEL_VALIDATION_OR_VIDEO_INFERENCE',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'training_protocol_sha256':sha(ROOT/'protocol/training_v4.json'),
 'new_conditions':conditions,'cached_control_conditions':controls,'baseline_root_remote':p['baseline_regression_root_remote'].rsplit('/',1)[0]+'/lowres_baseline_20261029',
 'videos':p['videos'],'prediction':p['prediction'],'counter_kwargs':p['counter_kwargs'],
 'validation_reference_definition':'SamepublishedclippedrotatedtorsopolygonAABB;CW90squareinput;IoU0.5matching,allunmatchedretained.',
 'validation_orientation':'clockwise90','validation_images':1571,'references':1864,'main_image_inference_stride':16,
 'actual_new_model_source_image_forwards_expected':63375,'new_validation_image_conditions':23565,
 'new_original_video_image_conditions':32625,'new_Toros_image_conditions':7185,'new_tracker_updates_expected':41010,
 'new_counter_paths_expected':90,'cached_control_tracker_updates_expected':16404,'cached_control_counter_paths_expected':36,
 'input_file_sha256':{name:sha(ROOT/'input'/name) for name in files},'geometry_module_sha256':sha(ROOT/'tools/geometry.py'),
 'old_counter_module_sha256':sha(base/'delivery/tools/run_baseline_v2.py'),
 'all15new_epoch10_weights_must_be_frozen_before_inference':True,'all_seeds_sizes_and_negative_results_retained':True,
 'crop_ROI_adopted':False,'detector_confidence':.2,'source_count_not_used_for_best_seed_selection':True,
 'new_independent_test':False,'PYNQ_joint5FPS_verified_by_this_offline_study':False,'whole_goal_complete':False}
# Derive the project root from the known absolute model checkpoint, not an
# unrelated regression directory; assert the intended path explicitly.
remote=Path(training['source_weights']).parent.parent.as_posix();protocol['baseline_root_remote']=remote+'/lowres_baseline_20261029'
assert protocol['baseline_root_remote']=='/share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029'
file=ROOT/'protocol/evaluation_v1.json';assert not file.exists();file.write_text(json.dumps(protocol,indent=2)+'\n')
print(json.dumps({'protocol_sha256':sha(file),'new_forwards':63375,'cached_controls':6,'new_conditions':15}))
