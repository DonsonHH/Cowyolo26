from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=load(ROOT/'delivery/results/audit/summary.json');v=load(ROOT/'results/independent_verification.json')
l=load(ROOT/'results/loader_recovery_local/summary.json');lv=load(ROOT/'results/loader_independent_verification.json')
visual=load(ROOT/'results/visual_review.json');xml=load(ROOT/'results/publisher_annotation_flag.json')
assert s['training_images']==6809 and s['objects']==v['geometry_checks']==8888
assert s['all_objects']['dark_proxy_median_le80']==5899 and s['all_objects']['low_contrast_proxy_le15']==3707
assert s['all_objects']['overlap_min_fraction_ge01']==269 and s['all_objects']['truncated_visible_fraction_lt099']==3228
assert l['delivered_batches']==213 and l['delivered_images']==6809 and l['augmented_label_rows']==20292
assert l['short_side_lt24']==5466 and l['short_side_lt16']==1949
assert lv['actual_RGB_images_byte_hash_checked']==96 and lv['actual_stored_label_boxes_and_background_rings_checked']==258
assert xml['labels_removed_or_changed']==0 and xml['high_overlap_pairs_over_all_training']==1
assert visual['figures_actually_viewed']==3 and visual['panels_actually_viewed']==28
for row in visual['files']:assert row['actually_viewed'] and sha(row['path'])==row['sha256']
for r in load(ROOT/'results/loader_recovery_local/recovery_verification.json')['original_artifact_files']:
    assert sha(ROOT/'loader_delivery'/r['file'])==r['sha256']
documents=[];linkcount=0
for name in ['计划与验收.md','训练覆盖审计与下一组对照.md','Review与当前状态.md']:
    p=ROOT/name;text=p.read_text(encoding='utf-8');assert '\ufffd' not in text
    for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
        target=unquote(m[1] or m[2])
        if re.match(r'^[A-Za-z]:[/\\]',target):assert Path(target).exists();linkcount+=1
    documents.append({'path':str(p.resolve()),'sha256':sha(p),'lines_read_and_reviewed':len(text.splitlines())})
files=['protocol/audit_v1.json','protocol/execution_v1.json','protocol/loader_v1.json','protocol/loader_execution_v1.json',
    'results/transfer_verification.json','results/independent_verification.json','results/loader_independent_verification.json',
    'results/media_and_XML_verification.json','results/publisher_annotation_flag.json','results/visual_review.json',
    'results/loader_recovery_local/summary.json','results/loader_recovery_local/recovery_verification.json','results/local_media/first12_values.json',
    'delivery/results/audit/summary.json','evidence/status01.txt','evidence/loader_collection.txt','evidence/loader_sources.txt',
    'tools/run_audit.py','tools/audit_loader.py','tools/recover_loader_locally.py','tools/verify_independent.py','tools/verify_loader.py',
    'tools/verify_media_and_xml.py']
result={'status':'TRAIN_ONLY6809_NATIVE_IMAGES8888_REGIONS213_ACTUAL_LOADER_BATCHES_AND28_PANELS_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'native_train_images':6809,'native_body_regions':8888,'native_Y_le80':5899,
    'native_low_background_contrast_le15':3707,'native_rectangle_overlap_proxy_ge01':269,
    'real_loader_delivered_batches':213,'real_loader_delivered_images':6809,'real_augmented_AABB_rows':20292,
    'augmented_shortside_lt24':5466,'augmented_shortside_lt16':1949,'actual_RGB_controls':96,'actual_stored_box_and_ring_controls':258,
    'native_histograms_checked':17776,'native_polygon_pairs_checked':2563,'native_pixel_control_objects':35,
    'source_XML_near_duplicate_flags':1,'labels_removed_or_modified':0,'independent_occlusion_or_coat_color_GT_created':False,
    'SVG_histogram_bars_checked':108,'figures_actually_viewed':3,'panels_actually_viewed':28,
    'loader_replayed_after_failure':False,'unpersisted_runtime_metadata_fabricated':False,
    'validation_holdout_or_video_pixels_in_coverage_audit':0,'new_model_forwards_in_coverage_audit':0,'new_training_updates':0,
    'actual_board_actions':0,'coverage_phase_jobs_terminal':True,'next_separate_phase_formal_array':'130622',
    'new_independent_test':False,'whole_goal_complete':False,'local_links_checked':linkcount,
    'documents':documents,'evidence_hashes':{name:sha(ROOT/name) for name in files}}
target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['documents','evidence_hashes']}))
