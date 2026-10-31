from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    old=PROJECT/'detector_torso_pairs_20261029';references=load(old/'input/images_and_references.json')['val']
    models=load(old/'protocol/pairs_v1.json')['models'];reg=load(PROJECT/'firststage_iou_regression_20261029/protocol/regression_v1.json')
    original=next(s for s in reg['sources'] if s['name']=='original_seed26');toros=next(s for s in reg['sources'] if s['name']=='toros_generic')
    videos=[{'name':'original','path':REMOTE+'/data/multicam_samples/camera1/2023-08-14T12-54-48.mp4',
    'sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1','width':2560,'height':1440,'fps':25,'decode_end_exclusive':10874,'inference_stride':5,
    'orientation':'clockwise90','axis':'y','perpendicular_ROI':[.34,.75],'scope_start_frame0':8912,'scope_end_exclusive':10874,
    'counter_replay_strides':[5],'human_down_total':12,'formal_event_scoring':False},
    {'name':'toros','path':REMOTE+'/phase3_diagnosis/data/mendeley_counting/extracted/Ground Truth/Toros.mp4',
    'sha256':'1172810976a09e1a75a8b0a69edf21038393aa6f6b1c1273b8d7c34f62146a6c','width':1920,'height':1080,'fps':30,
    'decode_end_exclusive':479,'inference_stride':1,'orientation':'original','axis':'x','perpendicular_ROI':[.1,.95],
    'scope_start_frame0':0,'scope_end_exclusive':479,'counter_replay_strides':[6,1],
    'reference_events':toros['reference_events'],'formal_event_scoring':True,'event_tolerance_s':2.}]
    save(ROOT/'input/validation_images.json',references);save(ROOT/'input/regression_sources.json',[original,toros])
    directory=ROOT/'input'
    for name in ['zone_counter.py','confirmation_counter.py','event_metrics.py']:shutil.copyfile(PROJECT/'firststage_iou_regression_20261029/input'/name,directory/name)
    shutil.copyfile(old/'tools/geometry.py',ROOT/'tools/geometry.py')
    conditions=[{'condition':m['name']+'_s'+str(size),'model':m['name'],'seed':m['seed'],'checkpoint':m['checkpoint'],'model_sha256':m['sha256'],'input_size':size}
    for m in models for size in [192,256,320]]
    p={'created_UTC':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_BEFORE_LOWRES_BASELINE_FEATURE_OR_VIDEO_FORWARD','sizes':[192,256,320],
    'models':models,'conditions':conditions,'target_board_frontend_fps':5,'target_frame_period_ms':200,
    'prediction':{'orientation_validation':'clockwise90','batch':16,'rect':False,'confidence':.2,'nominal_iou':.5,'half':False,'augment':False,'max_det':300,'device':0},
    'validation_images':1571,'validation_reference_objects':1864,'videos':videos,'counter_kwargs':reg['counter'],
    'tracker':'UnmodifiedUltralytics8.4.63BYTETrackerdefaultyaml;oneupdateperretainedsample;noageclockretuning.',
    'regression_gates':['original_seed26cached64012totalobservations/events','Torosofficialcached64030Hz6eventscore'],
    'baseline_regression_root_remote':REMOTE+'/firststage_iou_regression_20261029/results',
    'primary_Toros_sampling':'5Hzstride6;30Hzstride1samepredictionscontrolnotdeployment.',
    'expected_validation_image_forwards':1571*12,'expected_original_video_image_forwards':2175*12,'expected_Toros_video_image_forwards':479*12,
    'expected_total_detector_source_image_forwards':50700,'expected_total_tracker_updates':2175*12+80*12+479*12,
    'input_sha256':{f.name:sha(f) for f in directory.iterdir() if f.is_file()},'geometry_module_sha256':sha(ROOT/'tools/geometry.py'),
    'user_confirmed12_candidate_sha256':sha(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'),
    'all_model_resolution_counter_results_retained':True,'no_count_selected_model_adoption':True,
    'new_training_updates':0,'identity_encoder_forwards':0,'new_independent_test':False,'FPGA_performance_verified':False,'whole_goal_complete':False}
    save(ROOT/'protocol/baseline_v1.json',p);print(json.dumps({'protocol_sha256':sha(ROOT/'protocol/baseline_v1.json'),'conditions':len(conditions),'expected_source_image_forwards':50700,'tracker_updates':p['expected_total_tracker_updates']}))
if __name__=='__main__':main()
