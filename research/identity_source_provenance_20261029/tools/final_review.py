from pathlib import Path
from PIL import Image
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re,zlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    primary=load(ROOT/'results/primary_independent_audit.json');info=load(ROOT/'results/published_info_schema_audit.json')
    zip_check=load(ROOT/'results/zip_directory_independent_verification.json')
    geometry=load(ROOT/'results/coarse_geometry_independent_verification.json');fine=load(ROOT/'results/refined_geometry_independent_verification.json')
    pixel=load(ROOT/'results/photometry_and_event_link_verification.json');admission=load(ROOT/'results/evaluation_admission.json')
    visual=load(ROOT/'evidence/visual_review.json');geo_protocol=load(ROOT/'protocol/geometry_v1.json')
    for ID,name,file,elapsed,prefix in [('130396','gallery-source-geometry','geometry_status_05.txt','00:04:54','geometry_130396'),
                                      ('130399','gallery-source-refine','refine_status_02.txt','00:01:17','refine_130399'),
                                      ('130415','gallery-source-endpoints','endpoint_status_01.txt','00:00:02','endpoint_130415')]:
        assert re.search(ID+r'\s+'+name+r'\s+4gpu\s+COMPLETED\s+0:0\s+'+elapsed,(ROOT/'evidence'/file).read_text(encoding='utf-8'))
        assert (ROOT/'evidence'/(prefix+'.err')).stat().st_size==0
        assert 'Traceback' not in (ROOT/'evidence'/(prefix+'.out')).read_text(encoding='utf-8')
    for folder,archive,metadata,manifest,count in [
      ('geometry_delivery','geometry_coarse_delivery.tar.gz','geometry_coarse_delivery_record.json','geometry_manifest.json',7),
      ('refined_delivery','geometry_refined_delivery.tar.gz','geometry_refined_delivery_record.json','refined_manifest.json',58),
      ('endpoint_delivery','endpoint_delivery.tar.gz','endpoint_delivery_record.json','endpoint_manifest.json',7)]:
        record=load(ROOT/'evidence'/metadata);file=ROOT/archive
        assert file.stat().st_size==record['archive_bytes'] and sha(file)==record['archive_sha256']
        rows=load(ROOT/folder/manifest)['files'];assert len(rows)==count and record['files']==count+1
        for r in rows:assert (ROOT/folder/r['file']).stat().st_size==r['bytes'] and sha(ROOT/folder/r['file'])==r['sha256']
    for folder,relative in [('geometry_delivery','tools/geometry_probe.py'),('refined_delivery','tools/refine_geometry.py'),('endpoint_delivery','tools/check_endpoints.py')]:
        assert sha(ROOT/relative)==sha(ROOT/folder/relative)
    assert sha(ROOT/'protocol/geometry_v1.json')=='c86631074eb92b4bc7b0517e20ffabfee2ee0d4c76fdf3d40399e19e95f711b3'
    assert primary['source_text_files']==102 and primary['zip_entries']==103156 and primary['csv_members_found']==0
    assert zip_check['entries']==103156 and zip_check['CSV_members']==0 and zip_check['unique_member_names']==103156
    assert info['file_record_count']==101467 and info['explicit_frame_timestamp_crop_coordinate_identity_field_hits']==[]
    assert info['file_suffix_counts']=={'.jpg':101329,'.mp4':137,'.txt':1}
    assert info['leaf_field_counts']=={k:101467 for k in ['id','extent','format','label','sha1']}
    assert info['explicit_published_image_to_raw_frame_mapping_found'] is False
    assert len(primary['gallery_images_bound_to_official_archive_by_size_CRC_and_local_SHA256'])==30 and primary['all30_gallery_images_EXIF_empty'] is True
    assert primary['raw_video_original_archive_CRC_matches_local'] is True and info['raw_video_matches_published_SHA1'] is True
    zip_meta=load(ROOT/'evidence/zip_metadata/summary.json')
    for r in zip_meta['selected_members']:assert (ROOT/r['file']).stat().st_size==r['bytes'] and sha(ROOT/r['file'])==r['sha256'] and r['CRC32_verified'] is True
    assert sha(ROOT/'evidence/zip_metadata/readme.txt')==sha(ROOT/'evidence/primary/dataset_readme.txt')
    assert not (ROOT/'evidence/primary/author_appendix.pdf').read_bytes().startswith(b'%PDF-')
    assert geometry['coarse']['comparisons']==13050 and fine['verification']['comparisons']==300
    assert geometry['coarse']['candidates_with_transform_checked']==100 and fine['verification']['candidates_with_transform_checked']==82
    assert geometry['coarse']['inlier_points_checked']==1425 and fine['verification']['inlier_points_checked']==2001
    assert len(pixel['geometry_accepted_refined_template_photometry'])==5 and len(pixel['post_search_endpoint_checks'])==2
    core=pixel['core_same_source_capture_candidates']
    assert [r['source_frame0'] for r in core]==[9610,9685,9760] and all(r['NCC']>.99 and r['best_native_track_ID']==102 for r in core)
    assert pixel['related_event_id']=='E010_f9790_tid102' and pixel['related_query_snapshot_frame0']==9745
    assert pixel['post_search_endpoint_checks'][0]['independent_photometry']['NCC']<.8
    assert pixel['post_search_endpoint_checks'][1]['unchanged_geometry_pass'] is False and pixel['post_search_endpoint_checks'][1]['independent_photometry']['NCC']>.99
    assert admission['status']=='CURRENT_E010_ID009_AUG14_GALLERY_PAIR_EXCLUDED_FROM_INDEPENDENT_IDENTITY_EVALUATION'
    assert admission['source_link_verification_sha256']==sha(ROOT/'results/photometry_and_event_link_verification.json')
    assert admission['independent_event_identity_accuracy_admitted'] is False and admission['source_cow_identity_reference_promoted'] is False
    assert admission['training_or_new_threshold_label_admitted'] is False
    rasters=[]
    for folder in ['refined_delivery/results/geometry_refined','endpoint_delivery/results/endpoint_check','results/source_review']:
        for file in sorted((ROOT/folder).iterdir()):
            if file.suffix.lower() not in ['.jpg','.png']:continue
            with Image.open(file) as im:im.load();dimensions=list(im.size)
            rasters.append({'path':str(file.resolve()),'sha256':sha(file),'dimensions':dimensions})
    assert len(rasters)==66
    assert visual['current_sheets_viewed']==8 and visual['actual_image_panels_viewed']==95 and visual['empty_unfitted_panel_slots']==8
    for row in visual['current_sheets']:assert row['actual_visual_review']=='PASS' and sha(Path(row['path']))==row['sha256']
    retained={
      'human_count_confirmation_20261028/results/frozen_development_candidate.json':'5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b',
      'human_count_confirmation_20261028/evidence/user_confirmation.json':'fe8a895cd6ac71815ff8e2f6ad8d932a6453c41971b6b7a18ea9c2f743dd0f9f',
      'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json':'26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac',
      'phase3_diagnosis_20261026/inputs/multicam_original.mp4':geo_protocol['source_sha256']}
    for relative,digest in retained.items():assert sha(PROJECT/relative)==digest
    source=PROJECT/'confirmed12_capture_identity_20261029';prior=load(source/'results/final_review_v3.json')
    assert prior['source_confirmed_count_preserved']==12 and prior['source_identity_accuracy'] is None
    for name,digest in prior['evidence_hashes'].items():assert sha(source/name)==digest
    retained['confirmed12_capture_identity_20261029/results/final_review_v3.json']=sha(source/'results/final_review_v3.json')
    retained['confirmed12_capture_identity_20261029/delivery/results/replay/events.json']=sha(source/'delivery/results/replay/events.json')
    retained['confirmed12_rf_stream_20261029/results/final_review.json']=sha(PROJECT/'confirmed12_rf_stream_20261029/results/final_review.json')
    gallery=load(PROJECT/'identity_training_20261026/delivery/results/study/feature_index.json')['evaluation_gallery']
    for r in geo_protocol['gallery_images']:assert sha(Path(r['local_path']))==r['sha256']
    docs=[ROOT/'计划与验收.md',ROOT/'原视频身份来源核查与评价准入.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[];web_links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text and '\r\r' not in text
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
            elif url.startswith('https://'):web_links.append(url)
    evidence=['evidence/primary_manifest.json','evidence/secondary_metadata_manifest.json','evidence/author_source_manifest.json',
        'evidence/related_source_manifest.json','evidence/zip_directory/summary.json','evidence/zip_metadata/summary.json',
        'results/gallery_metadata_audit.json','results/primary_independent_audit.json','results/published_info_schema_audit.json',
        'results/zip_directory_independent_verification.json','protocol/geometry_v1.json','protocol/refinement_v1.json','protocol/endpoint_v1.json',
        'results/coarse_geometry_independent_verification.json','results/refined_geometry_independent_verification.json',
        'results/photometry_and_event_link_verification.json','results/source_review_record.json','results/key_evidence_figures_v2.json',
        'results/evaluation_admission.json','evidence/visual_review.json']
    result={'status':'OFFICIAL_SOURCE_MAPPING_AUDIT_AND_E010_ID009_SAME_PASSAGE_EVALUATION_EXCLUSION_REVIEWED',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'completed_jobs':['130396','130399','130415'],'job_exit_codes':['0:0','0:0','0:0'],
      'official_ZIP_entries_verified':103156,'official_image_files':101329,'official_video_files':137,'published_file_catalog_records':101467,
      'published_timestamp_CSV_members':0,'author_source_text_blobs_verified':102,'gallery_image_metadata_and_release_checks':30,
      'coarse_source_frames':435,'coarse_template_frame_comparisons':13050,'refined_source_frames':191,'refined_template_frame_comparisons':300,
      'independent_transform_candidates_checked':182,'independent_inlier_point_pairs_checked':3426,'known_source_controls':2,
      'independent_photometric_pairs':7,'strong_core_gallery_source_pairs':core,
      'source_trace_associated_event':'E010_f9790_tid102','affected_query_source_frame0':9745,
      'independent_identity_evaluation_admitted':False,'source_identity_truth_promoted':False,
      'first_endpoint_weak_match_preserved':True,'last_endpoint_geometry_rejection_preserved':True,
      'other25_gallery_absence_or_source_identity_error_inferred':False,'raw_count_model_gallery_thresholds_or_reference_changed':False,
      'current_confirmed12_milestone_preserved':True,'local_study_rasters_fully_decoded':66,
      'current_review_sheets_actually_viewed':8,'actual_image_panels_viewed':95,'unfitted_panel_slots':8,
      'local_links_checked':len(links),'web_links_present_in_docs':len(web_links),
      'new_identity_model_forwards':0,'new_detector_forwards':0,'new_training_updates':0,'actual_RF_or_PYNQ_execution':False,'whole_goal_complete':False,
      'evidence_hashes':{r:sha(ROOT/r) for r in evidence},'retained_artifact_hashes':retained,
      'documents':[{'path':str(path.resolve()),'sha256':sha(path)} for path in docs],'rasters':rasters}
    path=ROOT/'results/final_review.json';assert not path.exists();path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','retained_artifact_hashes','documents','rasters']}))
if __name__=='__main__':main()
