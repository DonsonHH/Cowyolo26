from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
training=PROJECT/'detector_factorial_20261029';freeze=load(training/'delivery/results/all_checkpoints_frozen.json')
oldcrop=PROJECT/'lowres_roi_20261029';crop=load(oldcrop/'protocol/roi_v1.json');full=load(training/'protocol/evaluation_v1.json')
models=[];conditions=[]
for r in freeze['conditions']:
    c=r['condition'];name=c['condition_id'];models.append({'name':name,'checkpoint':r['last_checkpoint'],'sha256':r['last_checkpoint_sha256']})
    conditions.append({'condition':name,'model':name,'input_size':c['imgsz'],'seed':c['seed'],'right_angle':c['right_angle']})
assert len(models)==len(conditions)==15
controls=load(oldcrop/'delivery/results/roi/input_tensor_controls.json');expected={}
for r in controls:
    key=r['scene']+'_f'+str(r['frame0'])+'_s'+str(r['input_size'])
    assert key not in expected or expected[key]==r['tensor_sha256'];expected[key]=r['tensor_sha256']
assert len(expected)==24
p={'status':'FROZEN_AFTER_EVENT_DIAGNOSIS_BEFORE_ANY_NEW_FIXED_CROP_MODEL_FORWARD','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'models':models,'conditions':conditions,'videos':crop['videos'],'prediction':full['prediction'],'counter_kwargs':full['counter_kwargs'],
 'full_input_results_remote':'/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029/results/evaluation',
 'full_input_summary_sha256':sha(training/'delivery/results/evaluation/summary.json'),
 'all15_checkpoint_freeze_sha256':sha(training/'delivery/results/all_checkpoints_frozen.json'),
 'counter_module_remote':'/share/home/renly/projects/idcoo_research_20261026/lowres_baseline_20261029/tools/run_baseline_v2.py',
 'counter_module_sha256':full['old_counter_module_sha256'],'prior_crop_protocol_sha256':sha(oldcrop/'protocol/roi_v1.json'),
 'event_diagnosis_verification_sha256':sha(PROJECT/'lowres_event_audit_20261029/results/independent_verification.json'),
 'old_fixed_crop_diagnosis_sha256':sha(PROJECT/'lowres_event_audit_20261029/results/crop_independent_verification.json'),
 'expected_NN_input_hashes_24_source_frame_sizes':expected,'new_detector_image_forwards_expected':39810,
 'full_cache_regression_traces_expected':45,'full_cache_regression_counter_paths_expected':90,
 'full_cache_regression_tracker_updates_expected':41010,'new_tracker_updates_expected':41010,'new_counter_paths_expected':90,
 'NN_input_anchor_hash_rows_expected':120,'reference_is_new_independent_test':False,'all_weights_and_negative_results_retained':True,
 'primary_case_for_media_not_count_selection':'S192_rot90_seed26','new_crop_or_threshold_search':False,
 'new_training_updates':0,'board_actions':0,'new_inference_job_submitted':False,'whole_goal_complete':False}
file=ROOT/'protocol/crop_v1.json';file.parent.mkdir(exist_ok=True);assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'protocol_sha256':sha(file),'new_detector_forwards_planned':39810,'NN_inputs_existing_hashes':len(expected),'job_submitted':False}))
