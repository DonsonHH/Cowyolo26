from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    old=PROJECT/'lowres_baseline_20261029';p=load(old/'protocol/baseline_v2_path_fix.json');videos=[]
    for spec in p['videos']:
        spec=dict(spec);W,H=spec['width'],spec['height'];lo,hi=spec['perpendicular_ROI']
        box=[math.floor(lo*W),0,math.ceil(hi*W),H] if spec['axis']=='y' else [0,math.floor(lo*H),W,math.ceil(hi*H)]
        spec['detection_crop_xyxy']=box;spec['crop_size_WH']=[box[2]-box[0],box[3]-box[1]]
        spec['pixel_control_frames']=[8995,9345,9790,10830] if spec['name']=='original' else [110,193,248,396]
        spec['source_long_dimension_ratio_full_to_crop']=max(W,H)/max(spec['crop_size_WH'])
        videos.append(spec)
    assert videos[0]['detection_crop_xyxy']==[870,0,1920,1440] and videos[1]['detection_crop_xyxy']==[0,108,1920,1026]
    directory=ROOT/'input';directory.mkdir(exist_ok=False)
    for name in ['zone_counter.py','confirmation_counter.py','event_metrics.py']:shutil.copyfile(old/'input'/name,directory/name)
    baseline_files=[]
    for spec in videos:
        for c in p['conditions']:
            folder=old/'delivery/results/baseline'/spec['name']/c['condition']
            for stride in spec['counter_replay_strides']:
                for name in ['stride'+str(stride)+'_counter_trace.json.gz','stride'+str(stride)+'_summary.json']:
                    f=folder/name;baseline_files.append({'relative':str(f.relative_to(old/'delivery')).replace('\\','/'),'sha256':sha(f)})
    source=old/'delivery/tools/run_baseline_v2.py'
    protocol={'status':'FROZEN_BEFORE_ANY_FIXED_CHANNEL_CROP_FORWARD','version':1,'created_UTC':datetime.now(timezone.utc).isoformat(),
    'baseline_protocol_sha256':sha(old/'protocol/baseline_v2_path_fix.json'),'baseline_review_sha256':sha(old/'results/final_review.json'),
    'baseline_summary_sha256':sha(old/'delivery/results/baseline/summary.json'),
    'baseline_root_remote':REMOTE+'/lowres_baseline_20261029','baseline_counter_module_path':REMOTE+'/lowres_baseline_20261029/tools/run_baseline_v2.py',
    'baseline_counter_module_sha256':sha(source),'baseline_files':baseline_files,'models':p['models'],'conditions':p['conditions'],'sizes':[192,256,320],
    'videos':videos,'prediction':p['prediction'],'counter_kwargs':p['counter_kwargs'],
    'input_module_sha256':{f.name:sha(f) for f in directory.iterdir()},'target_frontend_fps':5,'target_period_ms':200,
    'expected_network_source_image_forwards':31848,'expected_tracker_updates_new_crop':32808,'expected_tracker_updates_cached_full_regression':32808,
    'expected_counter_paths_each_input':72,'expected_nn_input_anchor_hashes':96,
    'independent_change':'Onlydetectorinputcrop;nativecoordinatesandsampling/tracker/countersunchanged;all12conditionsand2counterpathsretained.',
    'crop_boundaries_from_existing_counter_ROI_no_new_tuning':True,'allow_per_seed_or_image_special_rule':False,
    'restore_box':'CW90local[u1,v1,u2,v2]->[v1+x0,cropH-u2+y0,v2+x0,cropH-u1+y0];otherwiseadd[x0,y0,x0,y0].',
    'new_training_updates':0,'identity_encoder_forwards':0,'new_independent_test':False,'hardware_actions':0,
    'board_PID8082_terminal':'NOT_OBSERVED_DO_NOT_RESTART','PYNQ5FPS_proven':False,'whole_goal_complete':False}
    save(ROOT/'protocol/roi_v1.json',protocol)
    print(json.dumps({'protocol_sha256':sha(ROOT/'protocol/roi_v1.json'),'crops':[s['detection_crop_xyxy'] for s in videos],
    'linear_long_dimension_ratios':[s['source_long_dimension_ratio_full_to_crop'] for s in videos],'new_forwards':31848,'conditions':12}))
if __name__=='__main__':main()
