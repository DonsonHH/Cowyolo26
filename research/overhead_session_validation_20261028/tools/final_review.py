"""Final evidence audit for the ordinary-overhead session extension, not GT certification."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from collections import Counter
import ast,csv,hashlib,json,re
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def timestamp(s):
    day,clock=s.split('_');h,m,sec=map(int,clock.split('-'))
    return datetime.fromisoformat(day).replace(hour=h,minute=m,second=sec)

def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    selection_path=ROOT/'protocol/sessions_v1.json';s=load(selection_path);p_path=ROOT/'protocol/inference_v1.json';p=load(p_path)
    inventory=ROOT/'evidence/source_inventory.json';assert sha(inventory)==s['source_inventory_sha256']
    knownpath=PROJECT/'cows2021_adaptation_20261027/delivery/results/labels_v1/prepared_image_label_manifest.json'
    assert sha(knownpath)==s['actual_prepared_image_label_manifest_sha256']
    known=load(knownpath);times={timestamp('_'.join(r['original_filename'].split('_')[-2:])) for r in known}
    assert len(known)==8380 and len(times)==2217
    existing={r['sequence'] for r in load(inventory)['existing_local_server_samples']};eligible=[]
    for row in s['all_candidates']:
        t=timestamp(row['sequence']);reasons=[]
        if row['sequence'] in existing:reasons.append('previously_used_video')
        if str(t.date())=='2020-03-11':reasons.append('reserved_final_date_not_opened')
        if any(abs((t-d).total_seconds())<=10 for d in times):reasons.append('within_10s_of_existing_development_image_session')
        assert reasons==row['exclusion_reasons']
        if not reasons:eligible.append(row)
    eligible.sort(key=lambda r:r['capture_timestamp']);assert len(eligible)==213
    indices=[0,(len(eligible)-1)//3,2*(len(eligible)-1)//3,len(eligible)-1]
    assert [eligible[i] for i in indices]==s['selected'] and len(s['all_candidates'])==301
    assert all(not r['sequence'].startswith('2020-03-11') for r in s['selected'])
    manifest=load(ROOT/'evidence/fetch_manifest_resumed.json');admission_path=ROOT/'admission_delivery/results/admission/summary.json';admission=load(admission_path)
    assert manifest['protocol_sha256']==sha(selection_path)==p['selection_protocol_sha256']
    assert p['admission_summary_sha256']==sha(admission_path) and manifest['successful']==4
    assert manifest['successful_bytes']==162888404 and manifest['preserved_server_prefix_bytes']==11534336
    assert manifest['successful_HTTP_range_bytes']==151485144
    assert manifest['proxy_or_node_configuration_changed'] is False
    assert admission['frames_total']==637 and admission['development_image_exact_pixel_overlaps']==[]
    assert admission['pixel_overlap_screen_compared_to_images']==8380
    for r in manifest['files']:
        local=Path(r['local_path']);assert sha(local)==r['sha256'] and local.stat().st_size==r['bytes']
        matching=next(v for v in admission['videos'] if v['sequence']==r['sequence'])
        assert matching['source_sha256']==r['sha256'] and matching['fps']==30 and (matching['width'],matching['height'])==(1280,720)
    native_review=load(ROOT/'evidence/native_visual_review.json');visual=load(ROOT/'evidence/prediction_visual_review.json')
    assert sha(ROOT/'evidence/native_visual_review.json')==p['native_visual_review_sha256']
    assert native_review['source_pixels_seen_before_new_model_predictions'] is True and native_review['native_anchors_visually_reviewed']==20
    assert p['camera']=={'rotation_degrees':0,'axis':'x','perpendicular_ROI':[.05,.9],
                         'calibrated_from_native_scene_before_predictions':True,'A_to_B':'left_to_right'}
    assert p['counter']=={'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.0} and p['observation_hz']==5
    assert p['cold_start_each_clip'] is True and p['imgsz']==640 and p['detector_confidence']==.2
    summary_path=ROOT/'inference_delivery/results/inference/summary.json';summary=load(summary_path)
    assert summary['protocol_sha256']==sha(p_path) and summary['conditions_count']==8 and summary['new_model_forwards']==216
    verify_path=ROOT/'results/output_verification.json';verify=load(verify_path);independent_path=ROOT/'results/observation_diagnosis.json';independent=load(independent_path)
    assert verify['counter_updates_replayed']==independent['observation_ticks']==216
    assert verify['ROI_positions_independently_recomputed']==83 and independent['production_counter_modules_imported'] is False
    code=ast.parse((ROOT/'tools/diagnose_observations.py').read_text(encoding='utf-8'))
    imported=[]
    for node in ast.walk(code):
        if isinstance(node,ast.Import):imported.extend(n.name for n in node.names)
        elif isinstance(node,ast.ImportFrom):imported.append(node.module or '')
    assert 'zone_counter' not in imported and 'confirmation_counter' not in imported
    expected_raw={'official_yolo26n':[7,6,0,5],'accepted_seed26':[23,17,27,18]};event_counts={}
    for name in expected_raw:
        rows=[next(r for r in verify['predictions'] if r['sequence']==v['sequence'] and r['model']==name) for v in s['selected']]
        assert [r['raw_nonempty_samples'] for r in rows]==expected_raw[name]
        event_counts[name]=[r['predicted_A_to_B'] for r in rows]
        assert all(r['predicted_B_to_A']==0 for r in rows)
    assert event_counts=={'official_yolo26n':[0,0,0,0],'accepted_seed26':[0,0,1,0]}
    assert independent['only_event']=={'time_s':3.4,'track_id':1,'direction':'A->B','frame0':102}
    assert verify['media_files_full_decoded']==16 and verify['media_frames_full_decoded']==2548
    media=[]
    for r in verify['media']:
        path=Path(r['path']);assert sha(path)==r['sha256']
        assert r['ffprobe']['streams'][0]['nb_read_frames']==str(r['decoded_frames'])
        media.append({'path':str(path),'sha256':sha(path),'frames':r['decoded_frames']})
    images=[]
    for folder in [ROOT/'admission_delivery/results/admission',ROOT/'results/local_verification']:
        for path in sorted(folder.rglob('*')):
            if path.suffix.lower() not in ['.jpg','.png']:continue
            with Image.open(path) as im:im.load();shape=im.size
            images.append({'path':str(path),'sha256':sha(path),'dimensions':shape})
    assert len(images)==52
    assert visual['paired_contacts_viewed']==4 and visual['prediction_anchor_panels_viewed']==24
    assert visual['visual_acceptance'].startswith('PASS') and visual['continuous_browser_playback_or_controls_tested'] is False
    for filename in visual['viewed_files']:assert (ROOT/filename).exists()
    environment_path=ROOT/'evidence/completed_jobs_and_environment.txt';lines=environment_path.read_text(encoding='utf-8').splitlines();env=json.loads(lines[0])
    assert env['ultralytics']=='8.4.63' and env['no_new_model_forward_or_decode'] is True
    prior=load(PROJECT/'external_method_regression_20261028/protocol/regression_v1.json')
    expected={r['file']:r['sha256'] for r in prior['installed_source']}
    mapping={'trackers/track.py':'installed_track.py','trackers/byte_tracker.py':'installed_byte_tracker.py','cfg/trackers/bytetrack.yaml':'installed_bytetrack.yaml'}
    for r in env['installed_files']:
        assert r['sha256']==(expected[mapping[r['relative_path']]] if r['relative_path'] in mapping else prior['matching_source_sha256'])
    for jobid in ['130304','130305']:
        line=next(line for line in lines if line.split() and line.split()[0]==jobid)
        fields=line.split();assert fields[3:5]==['COMPLETED','0:0']
    source_candidate=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';candidate=load(source_candidate)
    assert sha(source_candidate)==p['accepted_12_candidate_sha256']=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
    assert candidate['human_total']==candidate['predicted_down']==12 and candidate['absolute_total_error']==0
    assert sha(Path(candidate['checkpoint_path']))==candidate['checkpoint_sha256']==p['models'][1]['checkpoint_sha256']
    catalog=PROJECT/'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json'
    assert sha(catalog)=='26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac'
    old_events=Path(candidate['source_event_record']['events_path']);assert sha(old_events)==candidate['source_event_record']['events_sha256']
    for name,digest in p['input_module_sha256'].items():assert sha(ROOT/'input'/name)==digest
    docs=[ROOT/'计划与验收.md',ROOT/'普通俯视新视频回放与研究决策.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
    result={'status':'FOUR_ORDINARY_OVERHEAD_SESSIONS_EIGHT_FROZEN_CONDITIONS_AND_LIMITS_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'selection_protocol_sha256':sha(selection_path),'inference_protocol_sha256':sha(p_path),
            'source_directory_entries':301,'eligible_sessions':213,'selected_sessions':4,'reserved_final_date_opened':False,
            'source_video_bytes':162888404,'source_frames':637,'prepared_images_screened_for_exact_RGB_matches':8380,'exact_RGB_matches':0,
            'near_duplicate_and_physical_ID_independence_proven':False,
            'model_conditions':8,'model_forward_calls':216,'training_updates':0,'independent_counter_paths':8,'counter_ticks_recomputed':216,
            'native_ROI_coordinates_recomputed':83,'official_raw_presence_frames':[7,6,0,5],'accepted_raw_presence_frames':[23,17,27,18],
            'per_clip_observation_ticks':27,'official_predicted_A_to_B':[0,0,0,0],'accepted_predicted_A_to_B':[0,0,1,0],
            'new_event_GT_available':False,'new_count_accuracy_or_recall_F1_claimed':False,
            'full_video_decode_files':16,'full_video_decode_frames':2548,'all_raster_files_decoded':52,
            'native_visual_anchors':20,'prediction_visual_anchors':24,'browser_playback_verified':False,
            'Slurm_jobs':[{'job':'130304','state':'COMPLETED','exit':'0:0','resources':'2 CPUs, 4 GiB, no GPU, 37s'},
                          {'job':'130305','state':'COMPLETED','exit':'0:0','resources':'1 V100S GPU, 4 CPUs, 12 GiB, 46s'}],
            'post_run_installed_source_hashes_match_prior':True,'post_run_capture_claimed_as_prerun_freeze':False,
            'current_source_human_confirmed_12_milestone_preserved':True,'current_source_29_conditions_unchanged':True,
            'whole_study_inputs_not_modified':True,'FPGA_execution_verified':False,'local_links_checked':len(links),
            'evidence_hashes':{str(path.relative_to(ROOT)):sha(path) for path in [summary_path,verify_path,independent_path,admission_path,environment_path,ROOT/'evidence/prediction_visual_review.json']},
            'media':media,'images':images,'documents':[{'path':str(path),'sha256':sha(path)} for path in docs],
            'previous_goal_turn_classification':'progress: user total12 accepted and successful development candidate frozen; camera scope changed to ordinary overhead',
            'this_goal_turn_classification':'progress: four new ordinary overhead videos obtained, eight fixed-model conditions run and independently diagnosed',
            'next_priority':'Complete event and boundary references plus ordinary overhead long video; preserve accepted12 candidate, then targeted training and board validation',
            'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['images','media','documents','evidence_hashes']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
