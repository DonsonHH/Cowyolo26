from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def file_record(local,remote):
    return {'local':str(local.resolve()),'path':remote,'bytes':local.stat().st_size,'sha256':sha(local)}
def stage(path,data):
    if path.exists():
        old=path.read_bytes()
        assert old==data or old.replace(b'\r\n',b'\n')==data.replace(b'\r\n',b'\n')
    else:path.write_bytes(data)
def main():
    input_dir=ROOT/'input';input_dir.mkdir(exist_ok=True);protocol_dir=ROOT/'protocol';protocol_dir.mkdir(exist_ok=True)
    assert not (protocol_dir/'regression_v1.json').exists()
    prior=PROJECT/'long_video_track_gap_20261029';current=load(prior/'results/final_review.json')
    assert current['new_long_seed26_predictions_before_after']==[11,12] and current['candidate_adopted'] is False
    implementation=(prior/'tools/firststage_control.py').read_text(encoding='utf-8')
    node=next(n for n in ast.parse(implementation).body if isinstance(n,ast.ClassDef) and n.name=='FirstStagePureIoUTracker')
    source=ast.get_source_segment(implementation,node)
    assert len(node.body)==1 and node.body[0].name=='_first_association'
    stage(input_dir/'firststage_tracker.py',('from ultralytics.trackers.byte_tracker import BYTETracker\nfrom ultralytics.trackers.utils import matching\n\n'+source+'\n').encode())
    for name,src in [('zone_counter.py',prior/'input/zone_counter.py'),('confirmation_counter.py',prior/'input/confirmation_counter.py'),
                     ('event_metrics.py',PROJECT/'external_method_regression_20261028/input/event_metrics.py')]:
        stage(input_dir/name,src.read_bytes())
    stage(input_dir/'publisher_gt_original.txt',(PROJECT/'external_method_regression_20261028/input/publisher_gt_original.txt').read_bytes())
    stage(input_dir/'publisher_event_summary.json',(PROJECT/'external_method_regression_20261028/delivery/reference_author_summary.json').read_bytes())
    modules={p.name:sha(p) for p in input_dir.iterdir() if p.is_file()}
    long=load(PROJECT/'long_video_fixed_replay_20261029/protocol/replay_v1.json')
    clock=load(PROJECT/'tracker_clock_20261028/protocol/clock_v1.json')
    ext=load(PROJECT/'external_method_regression_20261028/protocol/regression_v1.json')
    sources=[]
    for model in long['models']:
        name=model['name'];local=PROJECT/'long_video_fixed_replay_20261029/delivery/results'/name
        remote=REMOTE+'/long_video_fixed_replay_20261029/results/'+name
        files=[file_record(local/n,remote+'/'+n) for n in ['raw_detector_boxes.csv','post_tracker_boxes.csv','tracks.csv','observations.json','handoff_events_all_history.json','confirmed_only_events_all_history.json','summary.json']]
        sources.append({'name':'long_'+name,'scene':'new_long','model':name,'weights':{'path':model['checkpoint'],'sha256':model['sha256']},
            'files':files,'raw_path':remote+'/raw_detector_boxes.csv','raw_frame_key':'frame','height':1440,'width':2560,'fps':25,'stride':5,
            'history_end_frame0_exclusive':10125,'axis':'y','perpendicular_ROI':[.34,.75],'windows':long['windows'],
            'prior_remote_folder':remote,'reference_authority':'assistant_provisional_reference_unaccepted','formal_event_scoring_allowed':False})
    for seed in [26,27,28]:
        original=next(s for s in clock['sources'] if s['name']==f'full640_5hz_seed{seed}')
        weight=next(s for s in clock['weights'] if s['seed']==seed)
        raw_rel=Path(original['remote_folder'].removeprefix(REMOTE+'/'));local=PROJECT/raw_rel.parts[0]/'delivery'/Path(*raw_rel.parts[1:])
        files=[file_record(local/f['name'],original['remote_folder']+'/'+f['name']) for f in original['files']]
        for a,b in zip(files,original['files']):assert a['bytes']==b['bytes'] and a['sha256']==b['sha256']
        previous=PROJECT/f'confirmation_handoff_20261028/delivery/results/replay_v2/seed{seed}'
        prior_remote=REMOTE+f'/confirmation_handoff_20261028/results/replay_v2/seed{seed}'
        files.extend(file_record(previous/name,prior_remote+'/'+name) for name in ['observations.json','baseline_events.json','handoff_events.json','source_tracks.csv','source_warmup_tracks.csv','summary.json'])
        sources.append({'name':f'original_seed{seed}','scene':'original_clip','model':f'seed{seed}',
            'weights':{'path':weight['checkpoint'],'sha256':weight['sha256']},'files':files,
            'raw_path':original['remote_folder']+'/pretracker_boxes.csv','raw_frame_key':'frame','height':1440,'width':2560,'fps':25,'stride':5,
            'history_end_frame0_exclusive':10874,'axis':'y','perpendicular_ROI':[.34,.75],
            'windows':[{'name':'confirmed12_scope','start_frame0':8912,'end_frame0_exclusive':10874}],
            'prior_remote_folder':prior_remote,'reference_authority':'user_confirmed_down_total12_development_clip',
            'human_down_total':12,'formal_event_scoring_allowed':False})
    for model in ext['models']:
        local_folder=PROJECT/'external_method_regression_20261028/delivery/original_cache'/model['name']
        files=[]
        for f in model['cache_files']:
            local=local_folder/Path(f['path']).name;row=file_record(local,f['path']);assert row['sha256']==f['sha256'];files.append(row)
        prior_remote=REMOTE+'/external_method_regression_20261028/results/'+model['name']+'_installed'
        previous=PROJECT/'external_method_regression_20261028/delivery/results'/(model['name']+'_installed')
        for name in ['observations.json','confirmed_only_events.json','handoff_events.json','summary.json']:files.append(file_record(previous/name,prior_remote+'/'+name))
        sources.append({'name':'toros_'+model['name'],'scene':'toros_used_reverse','model':model['name'],'weights':model['checkpoint'],
            'files':files,'raw_path':next(f['path'] for f in model['cache_files'] if f['path'].endswith('raw_detector_boxes.csv')),
            'raw_frame_key':'frame','height':1080,'width':1920,'fps':30,'stride':1,'history_end_frame0_exclusive':479,
            'axis':'x','perpendicular_ROI':[.1,.95],'windows':[{'name':'publisher6_scope','start_frame0':0,'end_frame0_exclusive':479}],
            'prior_remote_folder':prior_remote,'reference_authority':'already_used_publisher_trajectory_derived_six_events',
            'reference_events':ext['reference_events'],'formal_event_scoring_allowed':True,'event_tolerance_s':2.})
    assert len(sources)==9
    full_updates=sum(len(range(0,s['history_end_frame0_exclusive'],s['stride'])) for s in sources)*2
    assert full_updates==31166
    protocol={'name':'Firststage-only IoU candidate paired regression, all predefined models and scenes retained',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'prior_candidate_review_sha256':sha(prior/'results/final_review.json'),
       'prior_candidate_class_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'input_modules':modules,
       'installed_source':long['installed_source'],'matching_source_sha256':long['matching_source_sha256'],
       'counter':long['counter'],'variants':['original_fused','firststage_pure_IoU'],'sources':sources,
       'baseline_gate_required_before_candidate_runs':True,'full_tracker_runs':18,'expected_full_tracker_updates':full_updates,
       'counter_paths':36,'fixed_overlap_candidate_IoU':.5,'overlap_candidates_are_not_physical_duplicates':True,
       'fixed_visual_anchors':{'original_clip':[9345,9380],'new_long':[2675,2720,3825],'toros_used_reverse':[245,397]},
       'current_confirmed12_candidate_sha256':sha(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'),
       'current_29_condition_catalog_sha256':sha(PROJECT/'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json'),
       'new_long_draft_sha256':sha(PROJECT/'overhead_positive_reference_20261028/reference/assistant_event_draft_v1.json'),
       'new_long_timing_draft_sha256':sha(PROJECT/'event_timing_refinement_20261029/reference/assistant_event_timing_v2.json'),
       'no_parameter_selection_or_new_training':True,'candidate_adoption_not_automatic':True,'new_independent_test':False,
       'new_detector_forwards':0,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target=protocol_dir/'regression_v1.json';target.write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'sources':9,'full_tracker_runs':18,'counter_paths':36,'tracker_updates':full_updates,'protocol_sha256':sha(target)}))
if __name__=='__main__':main()
