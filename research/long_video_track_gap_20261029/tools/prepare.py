from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    prior=PROJECT/'long_video_fixed_replay_20261029';p=json.loads((prior/'protocol/replay_v1.json').read_text(encoding='utf-8'))
    final=json.loads((prior/'results/final_review.json').read_text(encoding='utf-8'))
    assert final['handoff_down_predictions']['seed26']==11 and final['whole_goal_complete'] is False
    inputs=ROOT/'input';inputs.mkdir(exist_ok=False)
    module={}
    for name in ['zone_counter.py','confirmation_counter.py']:
        dest=inputs/name;dest.write_bytes((prior/'input'/name).read_bytes());module[name]=sha(dest)
    source=prior/'delivery/results/seed26'
    records=[]
    for name in ['raw_detector_boxes.csv','post_tracker_boxes.csv','tracks.csv','observations.json',
                 'handoff_events_all_history.json','confirmed_only_events_all_history.json','summary.json']:
        file=source/name;records.append({'name':name,'sha256':sha(file),'bytes':file.stat().st_size})
    spec=next(x for x in p['models'] if x['name']=='seed26')
    value={'name':'Native long-video seed26 fixed-output gap reproduction before association instrumentation',
           'created_UTC':datetime.now(timezone.utc).isoformat(),'prior_protocol_sha256':sha(prior/'protocol/replay_v1.json'),
           'prior_review_sha256':sha(prior/'results/final_review.json'),
           'source_folder':REMOTE+'/long_video_fixed_replay_20261029/results/seed26','source_files':records,
           'source_sha256':p['source_sha256'],'weights':spec,'installed_source':p['installed_source'],
           'matching_source_sha256':p['matching_source_sha256'],'input_modules':module,
           'history_start0':0,'history_end0_exclusive':10125,'stride':5,'source_fps':25,
           'native_size_WH':[2560,1440],'ROI_x':[.34,.75],'counter':p['counter'],
           'target_ID':19,'fragment_ID':23,'snapshot_before_frame0':2650,'short_replay_frames':list(range(2650,2676,5)),
           'diagnostic_signal':'Expected under assistant same-cow case hypothesis: recover original ID19 on a raw-supported observation and emit its A-to-B event by frame2675.',
           'signal_is_independent_human_identity_ground_truth':False,
           'reason_not_remove_neighbour_frames_or_tracks':'Association depends on complete competitor matrices; preserve actual state and every neighbour rather than change the mechanism under study.',
           'new_model_forwards':0,'new_training_updates':0,'formal_scores_computed':False,'whole_goal_complete':False}
    folder=ROOT/'protocol';folder.mkdir(exist_ok=False);target=folder/'reproduce_v1.json';target.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'protocol_sha256':sha(target),'cached_observation_ticks':2025,'short_signal_updates':6,'new_detector_forwards':0}))
if __name__=='__main__':main()
