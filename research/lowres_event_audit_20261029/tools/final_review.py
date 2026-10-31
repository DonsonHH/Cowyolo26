from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
from PIL import Image
import json,hashlib,re,gzip
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
s=load(ROOT/'results/summary.json');v=load(ROOT/'results/independent_verification.json')
c=load(ROOT/'crop_results_v2/summary.json');cv=load(ROOT/'results/crop_independent_verification.json')
media=load(ROOT/'results/media_manifest.json');mv=load(ROOT/'results/media_and_reference_verification.json')
assert s['cached_conditions']==27 and c['cached_conditions']==12 and len(s['cases'])==54 and len(c['cases'])==24
assert v['cases']==54 and v['reference_case_rows']==31374 and v['matching_problems']==38664 and v['independent_counter_oracle_paths']==162
assert cv['cases']==24 and cv['reference_case_rows']==13944 and cv['matching_problems']==17184 and cv['independent_counter_oracle_paths']==72
assert v['actual_larger_than_some_oracle_case_count']==13 and v['oracles_are_not_monotonic_upper_bounds'] is True
assert v['primary_direct_count']==6 and v['primary_6_unmapped_reference_tracks_fail_presence_oracle'] is True and v['primary_iou05_iou03_oracle_counts_same'] is True
assert c['counter_oracle_paths']==72
case=load(ROOT/'results/S192_rot90_seed26/iou05/case.json');miss=[r for r in case['tracks'] if r['actual_direct_corresponding_down_events']==0]
assert [r['reference_track_id'] for r in miss]==[93,94,96,103,98,102]
assert [(r['raw_correspondence_samples'],r['reference_box_samples']) for r in miss]==[(34,47),(3,15),(33,52),(23,35),(27,66),(51,75)]
assert [(r['longest_stable_region_runs']['presence_using_reference_center']['A'],r['longest_stable_region_runs']['presence_using_reference_center']['B']) for r in miss]==[(2,22),(0,2),(2,8),(0,20),(6,2),(1,15)]
assert list(case['oracle_down_counts'].values())==[6,6,5] and case['actual_unmapped_event_count']==0
assert mv['status']=='ALL12_REFERENCE_EVENTS_AND18_ABSOLUTE_PTS_SELECTIONS36_PANEL_METADATA_VERIFIED'
assert mv['reference_self_events_independently_recomputed']==12 and len(mv['native_source_frame_pixel_checks'])==18
assert all(r['independent_absolute_PTS_selection_matches_frame_select_exact'] for r in mv['native_source_frame_pixel_checks'])
assert len(media['pages'])==6 and sum(p['image_panels'] for p in media['pages'])==36
visual=[]
for row in media['pages']:
    file=Path(row['path']);assert sha(file)==row['sha256']
    with Image.open(file) as image:image.load();assert image.size==(1920,900)
    visual.append({'path':str(file.resolve()),'sha256':sha(file),'image_panels':6,
       'actually_viewed':True,'review':'Openedall3sourceframesand3nativedetails;referenceblue/rawgreen,ROI,frameindicesandlabelslegible;missesvisible;notGT.'})
visual_record={'figures_actually_viewed':6,'image_panels_actually_viewed':36,'pages':visual}
if (ROOT/'results/visual_review.json').exists():assert load(ROOT/'results/visual_review.json')==visual_record
else:save(ROOT/'results/visual_review.json',visual_record)
nextp=PROJECT/'factorial_lane_crop_20261029/protocol/crop_v1.json';nextprotocol=load(nextp)
assert len(nextprotocol['conditions'])==15 and nextprotocol['new_detector_image_forwards_expected']==39810
assert nextprotocol['new_inference_job_submitted'] is False and nextprotocol['new_crop_or_threshold_search'] is False
original=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'
assert sha(original)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
accepted=load(original);retained={original.relative_to(PROJECT).as_posix():sha(original)}
for key,hk in [('reference_path','reference_sha256'),('checkpoint_path','checkpoint_sha256')]:
    file=Path(accepted[key]);assert sha(file)==accepted[hk];retained[file.relative_to(PROJECT).as_posix()]=sha(file)
file=Path(accepted['source_event_record']['events_path']);assert sha(file)==accepted['source_event_record']['events_sha256'] and len(load(file))==12
retained[file.relative_to(PROJECT).as_posix()]=sha(file)
for protocolfile in ['protocol/audit_v1.json','protocol/audit_crop_v1.json']:
    p=load(ROOT/protocolfile)
    for cache in p['caches']:
        for kind in ['raw','trace','summary']:assert sha(cache[kind+'_file'])==cache[kind+'_sha256']
docs=[ROOT/'计划与验收.md',ROOT/'低分辨率漏计分解与下一步.md',ROOT/'Review与当前状态.md',PROJECT/'factorial_lane_crop_20261029/计划与验收.md',
      PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
links=[]
for doc in docs:
    text=doc.read_text(encoding='utf-8');assert '\ufffd' not in text
    for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',text):
        link=match.group(1) or match.group(2)
        if link.startswith(('http://','https://','#')):continue
        file=Path(unquote(link.split('#')[0]));file=file if file.is_absolute() else doc.parent/file
        assert file.exists(),(doc,link);links.append({'document':str(doc.resolve()),'link':link})
evidence=['protocol/audit_v1.json','protocol/audit_crop_v1.json','protocol/visual_v1.json','input/reference_boxes.json',
 'input/reference_admissions.json','input/reference_events.json','results/summary.json','crop_results_v2/summary.json',
 'results/independent_verification.json','results/crop_independent_verification.json','results/media_and_reference_verification.json',
 'results/actual_frame_timestamps.json','results/timestamp_seek_diagnostic.json','results/crop_report_count_correction.json',
 'results/visual_review.json','results/all_conditions.csv','results/crop_conditions.csv','results/media_manifest.json',
 'results/reference_self_regression.json','results/S192_rot90_seed26/iou05/case.json','results/S192_rot90_seed26/iou03/case.json']
result={'status':'39_CACHED_CONDITIONS78_DIAGNOSTIC_CASES234_ORACLE_PATHS_AND36_NATIVE_PIXEL_PANELS_REVIEWED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'read_only_diagnosis_phase_complete':True,'whole_goal_complete':False,
 'full_input_cached_conditions':27,'fixed_crop_cached_conditions':12,'fixed_IoU_levels':[.5,.3],'diagnostic_cases':78,
 'reference_tracks':12,'reference_box_samples':581,'unique_raw640_prior_admissions':12,
 'case_reference_rows':45318,'independent_assignment_problems':55848,'independent_counter_oracle_paths':234,
 'reference_self_events_and_exact_frames_verified':12,'primary_case':'S192_rot90_seed26','primary_actual_down_count':6,
 'primary_presence_raw_center_post_center_oracle_counts':[6,6,5],
 'primary_unmapped_reference_tracks':[93,94,96,103,98,102],'primary6_fail_presence_oracle_at_both_IoU_levels':True,
 'primary_entry_region_insufficient_cases':5,'primary_exit_region_insufficient_cases':1,
 'actual_above_some_oracle_full_input_conditions':13,'oracles_are_not_monotonic_upper_bounds':True,
 'reference_is_independent_GT':False,'actual_animal_identity_labels_created':False,'formal_reference_F1_admitted':False,
 'new_network_forwards':0,'new_training_updates':0,'PYNQ_actions':0,'global_runtime_pipeline_changed':False,
 'source_frame_scope':[8912,10873],'actual_PTS_native_frame_pixel_checks':18,'figures_actually_viewed':6,'image_panels_actually_viewed':36,
 'next_fixed_crop_conditions':15,'next_fixed_crop_detector_forwards_planned':39810,'next_crop_job_submitted':False,
 'next_crop_protocol_sha256':sha(nextp),'original_human12_milestone_preserved':True,'foreground_background_joint5FPS_proven':False,
 'retained_artifact_hashes':retained,'evidence_hashes':{r:sha(ROOT/r) for r in evidence},
 'documents':[{'path':str(doc.resolve()),'sha256':sha(doc)} for doc in docs],'local_links_checked':len(links),
 'manual_numeric_scope_and_oracle_limitation_review_completed':True}
save(ROOT/'results/final_review.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['retained_artifact_hashes','evidence_hashes','documents']}))
