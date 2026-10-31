from pathlib import Path
from PIL import Image
from datetime import datetime,timezone
from urllib.parse import unquote
import argparse,hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='final_review.json');args=parser.parse_args()
    assert Path(args.output).name==args.output and args.output.endswith('.json')
    p=load(ROOT/'protocol/chain_v1.json');s=load(ROOT/'delivery/results/replay/summary.json')
    v=load(ROOT/'results/independent_verification.json');visual=load(ROOT/'evidence/visual_review.json');render=load(ROOT/'results/review_images_record.json')
    for ID,name,file,elapsed,prefix in [('130360','confirmed12-capture-id','status_01.txt','00:00:53','replay_130360'),
                                      ('130361','confirmed12-source-verify','verify_status_01.txt','00:00:20','verify_130361')]:
        assert re.search(ID+r'\s+'+name+r'\s+cu\s+COMPLETED\s+0:0\s+'+elapsed,(ROOT/'evidence'/file).read_text())
        assert (ROOT/'evidence'/(prefix+'.err')).stat().st_size==0
        assert 'Traceback' not in (ROOT/'evidence'/(prefix+'.out')).read_text()
    record=load(ROOT/'evidence/delivery_record.json');archive=ROOT/'chain_delivery.tar.gz'
    assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256']
    rows=load(ROOT/'delivery/delivery_manifest.json')['files'];assert len(rows)==120 and record['files']==121
    for row in rows:assert (ROOT/'delivery'/row['file']).stat().st_size==row['bytes'] and sha(ROOT/'delivery'/row['file'])==row['sha256']
    assert sha(ROOT/'protocol/chain_v1.json')==s['protocol_sha256']=='546bb4205dd2d253a256b0e47216f3ef763731dae3ebe949ea95de161a9d8ab9'
    for name in ['tools/run_chain.py','tools/verify_remote.py','tools/identity_worker.py']:assert sha(ROOT/name)==sha(ROOT/'delivery'/name)
    for name,digest in p['input_module_sha256'].items():assert sha(ROOT/'input'/name)==sha(ROOT/'delivery/input'/name)==digest
    old_protocol=load(PROJECT/'video_chain_20261026/protocol/video_chain_v1.json')
    assert p['identity']==old_protocol['identity'] and p['snapshots']==old_protocol['snapshots']
    upstream=PROJECT/'video_chain_20261026/tools/identity_worker.py';code=(ROOT/'tools/identity_worker.py').read_text(encoding='utf-8')
    assert sha(upstream)==p['upstream_identity_worker_sha256'] and sha(ROOT/'tools/identity_worker.py')==p['identity_worker_sha256']
    start=code.index("        export_path=Path(protocol['identity_gallery_export_path'])")
    end=code.index("        result_queue.put({'kind':'ready'",start);code=code[:start]+code[end:]
    inserted="                assert hashlib.sha256((project/'identity_training'/row['relative_path']).read_bytes()).hexdigest()==row['sha256']\n"
    assert code.count(inserted)==1;code=code.replace(inserted,'')
    lines=code.splitlines(keepends=True)
    filtered=[line for line in lines if not any(key in line for key in ["'query_tensor_sha256':","'query_tensor_shape':","'identity_scores':"])]
    assert len(lines)-len(filtered)==3 and ''.join(filtered)==upstream.read_text(encoding='utf-8')
    assert s['counter_events_exact'] is True and s['event_count']==s['native_photos']==s['worker_completed_jobs']==12
    assert v['counter_ticks_recomputed']==2175 and v['snapshot_consider_inputs']==282 and v['selected_candidate_quality_source_checks']==36
    assert v['model_query_results']==60 and v['image_cosine_dotproducts_verified']==1800 and v['per_identity_scores_verified']==360
    assert v['real_fresh_process_repeated_queries']==60 and v['gallery_self_query_controls']==5
    assert v['total_query_forward_calls_including_repeats_and_control']==125
    assert s['task_terminal_status_counts']=={'ALL_CONDITIONS_REJECTED':10,'CANDIDATE_THRESHOLD_PASSED_UNVERIFIED':2}
    assert list(s['threshold_pass_counts_by_condition'].values())==[0,0,1,1,1]
    passing=[r for r in v['passing_cases'] if r['passing_conditions']]
    assert [r['event_id'] for r in passing]==['E005_f9345_tid95','E010_f9790_tid102']
    assert [[c['candidate_anonymous_id'] for c in r['passing_conditions']] for r in passing]==[['020'],['009','009']]
    assert s['jobs_finishing_after_frontend_EOF']==0 and s['jobs_overlapping_cached_frontend_host_intervals']==12
    assert s['snapshot_bank_peak_bytes']==12508422<=s['snapshot_bank_byte_limit']==33554432 and s['snapshot_bank_evictions']==0
    assert s['max_observed_inflight_including_service']==2 and s['worker_exit_code']==0
    events=load(ROOT/'delivery/results/replay/events.json')
    assert len(events)==12 and all(e['verified_identity'] is False and e['source_identity_reference'] is None for e in events)
    assert s['foreground_detector_ran_in_this_job'] is False and s['source_identity_accuracy'] is None
    assert visual['status']=='FIVE_CAPTURE_AND_CANDIDATE_SHEETS_THIRTY_IMAGE_PANELS_ACTUALLY_VIEWED'
    assert len(visual['sheets'])==5 and sum(r['image_panels'] for r in visual['sheets'])==30
    raster=[]
    for row in v['rasters']:
        path=Path(row['path']);assert sha(path)==row['sha256']
        with Image.open(path) as im:im.load()
        raster.append(row)
    for row in visual['sheets']:
        path=Path(row['path']);assert sha(path)==row['sha256'] and row['actual_visual_review']=='PASS'
        with Image.open(path) as im:im.load()
        raster.append({'path':str(path),'sha256':sha(path)})
    assert len(raster)==77
    for comparison in render['candidate_comparisons']:
        assert sha(Path(comparison['gallery_path']))==comparison['gallery_sha256']==comparison['gallery_metadata']['sha256']
        assert sha(Path(comparison['query_path']))==comparison['query_sha256']
    assert (ROOT/'evidence/snapshot_tests.txt').read_text().rstrip().endswith('OK') and 'Ran 8 tests' in (ROOT/'evidence/snapshot_tests.txt').read_text()
    runtime=load(ROOT/'evidence/environment_metadata.json');assert runtime['packages']['torch']=='2.8.0' and runtime['packages']['torchvision']=='0.23.0'
    retained={
      'human_count_confirmation_20261028/results/frozen_development_candidate.json':p['frozen_development_candidate_sha256'],
      'human_count_confirmation_20261028/evidence/user_confirmation.json':p['human_confirmation_sha256'],
      'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json':'26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac',
      'firststage_iou_regression_20261029/results/final_review.json':sha(PROJECT/'firststage_iou_regression_20261029/results/final_review.json'),
      'identity_training_20261026/delivery/results/study/feature_index.json':p['identity']['feature_index_sha256'],
      'identity_training_20261026/delivery/results/study/summary.json':p['identity']['study_summary_sha256'],
      'phase3_diagnosis_20261026/inputs/multicam_original.mp4':p['source_video_sha256']}
    for relative,digest in retained.items():assert sha(PROJECT/relative)==digest
    accepted=load(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json')
    assert accepted['human_total']==accepted['predicted_down']==12 and accepted['absolute_total_error']==0
    prior=load(PROJECT/'firststage_iou_regression_20261029/results/final_review.json');assert prior['candidate_global_replacement_adopted'] is False
    for file in p['cache_files']:assert sha(Path(file['local']))==file['sha256']
    docs=[ROOT/'计划与验收.md',ROOT/'12事件原图抓拍与身份查询结果.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text and '\r\r' not in text
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            target=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',target):assert Path(target).exists(),target;links.append(target)
    evidence=['protocol/chain_v1.json','results/independent_verification.json','results/review_images_record.json','evidence/visual_review.json',
              'evidence/delivery_record.json','evidence/status_01.txt','evidence/verify_status_01.txt','evidence/snapshot_tests.txt','evidence/environment_metadata.json']
    result={'status':'CONFIRMED12_NATIVE_CAPTURE_REAL_IDENTITY_QUERIES_AND_UNVERIFIED_CANDIDATES_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'jobs_completed':['130360','130361'],'job_exit_codes':['0:0','0:0'],
            'source_decode_frames':10874,'cached_counter_update_ticks':2175,'source_confirmed_count_preserved':12,
            'photos':12,'tasks_completed':12,'real_first_queries':60,'real_repeated_queries':60,'interface_self_query_controls':5,
            'total_query_forward_calls':125,'independent_image_dotproducts':1800,'independent_identity_scores':360,
            'source_photo_JPEG_reencoding_checks':12,'source_quality_pixel_checks':36,'snapshot_consider_inputs':282,
            'all_conditions_rejected_events':10,'unverified_candidate_events':2,
            'candidate_public_anonymous_IDs':['020','009'],'verified_source_identities':0,'source_identity_accuracy':None,
            'worker_finished_after_frontend_EOF':0,'retained_snapshot_peak_bytes':12508422,'snapshot_byte_limit':33554432,
            'snapshot_behavior_tests':8,'raster_files_fully_decoded':77,'actual_contact_sheets_viewed':5,'actual_image_panels_viewed':30,
            'local_links_checked':len(links),'archive_members':121,'worker_delta_is_audit_only_verified':True,
            'current_count_model_and_thresholds_unchanged':True,'new_detector_forwards':0,'new_training_updates':0,
            'actual_RF_hardware_connected':False,'FPGA_execution_verified':False,'whole_goal_complete':False,
            'evidence_hashes':{r:sha(ROOT/r) for r in evidence},'retained_artifact_hashes':retained,
            'documents':[{'path':str(path.resolve()),'sha256':sha(path)} for path in docs],'rasters':raster}
    path=ROOT/'results'/args.output;assert not path.exists();path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','retained_artifact_hashes','documents','rasters']}))
if __name__=='__main__':main()
