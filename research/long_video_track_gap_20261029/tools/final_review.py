from pathlib import Path
from PIL import Image
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=load(ROOT/'protocol/reproduce_v1.json');diagnostic=load(ROOT/'results/independent_verification.json')
    control=load(ROOT/'results/control_independent_verification.json');media=load(ROOT/'results/paired_media_verification.json')
    visual=load(ROOT/'evidence/visual_review.json');status=(ROOT/'evidence/control_status_01.txt').read_text()
    for job,name,elapsed in [('130347','long-video-gap-repro','00:00:11'),('130348','long-video-gap-probe','00:00:04'),('130349','long-firststage-control','00:00:05')]:
        assert re.search(job+r'\s+'+name+r'\s+cu\s+COMPLETED\s+0:0\s+'+elapsed,status)
    for prefix in ['reproduce_130347','probe_130348','control_130349']:
        assert (ROOT/'evidence'/(prefix+'.err')).stat().st_size==0
        assert 'Traceback' not in (ROOT/'evidence'/(prefix+'.out')).read_text()
    assert 'EXPECTED_SIGNAL_EXIT_CODES=1,1' in (ROOT/'evidence/reproduce_130347.out').read_text()
    manifests=[]
    for folder,archive,record,manifest_name,expected in [
      ('delivery','gap_diagnostic_delivery.tar.gz','delivery_record.json','delivery_manifest.json',21),
      ('control_delivery','firststage_control_delivery.tar.gz','control_delivery_record.json','control_delivery_manifest.json',37)]:
        r=load(ROOT/'evidence'/record);path=ROOT/archive
        assert path.stat().st_size==r['archive_bytes'] and sha(path)==r['archive_sha256']
        rows=load(ROOT/folder/manifest_name)['files'];assert len(rows)==expected and r['files']==expected+1
        for row in rows:assert (ROOT/folder/row['file']).stat().st_size==row['bytes'] and sha(ROOT/folder/row['file'])==row['sha256']
        manifests.append({r['file']:r['sha256'] for r in rows})
    for name,digest in manifests[0].items():assert manifests[1][name]==digest
    prior_root=PROJECT/'long_video_fixed_replay_20261029';prior=load(prior_root/'results/final_review.json')
    assert sha(prior_root/'results/final_review.json')==p['prior_review_sha256']
    for relative,digest in prior['source_and_retained_artifact_hashes'].items():assert sha(PROJECT/relative)==digest
    for row in p['source_files']:assert sha(prior_root/'delivery/results/seed26'/row['name'])==row['sha256']
    weights=PROJECT/'cows2021_adaptation_20261027/delivery/results/training/seed26/weights/last.pt'
    assert sha(weights)==p['weights']['sha256']
    assert diagnostic['real_matrix_entries_verified']==51 and diagnostic['partial_assignments_enumerated']==26
    assert diagnostic['firststage_global_assignments_verified']==6 and diagnostic['original_full_outputs_preserved'] is True
    assert diagnostic['diagnostic_frame_summaries'][-1]['hypothetical_pure_IoU_pair_within_limit'] is False
    assert control['counter_paths']==4 and control['native_ROI_centers_verified']==600
    assert [r['down_events'] for r in control['results']]==[11,12]
    assert control['candidate_short_signal']=='GREEN' and control['baseline_short_signal']=='RED'
    assert control['prediction_time_multiset_added']==[[2675,'A->B'],[3840,'A->B']]
    assert control['prediction_time_multiset_removed']==[[3845,'A->B']]
    assert control['candidate_adopted'] is False and control['old_confirmed12_clip_regression_pending'] is True
    assert media['source_frames_hash_checked']==media['video_frames_fully_decoded']==625
    for row in media['media']:assert row['strict_decode']=='PASS' and row['fps']==5 and sha(Path(row['path']))==row['sha256']
    for row in media['source_records']:assert sha(Path(row['path']))==row['sha256']
    assert len(visual['sheets'])==6 and sum(x['panels'] for x in visual['sheets'])==12
    rasters=[]
    for row in visual['sheets']:
        path=Path(row['path']);assert sha(path)==row['sha256'] and row['actual_visual_review']=='PASS'
        with Image.open(path) as image:image.verify()
        rasters.append({'path':str(path),'sha256':sha(path)})
    docs=[ROOT/'计划与验收.md',ROOT/'新片轨迹分段定位与单因素对照.md',ROOT/'Review与当前状态.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text and '\r\r' not in text
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
    evidence=['protocol/reproduce_v1.json','protocol/association_probe_v1.json','protocol/firststage_control_v1.json',
              'results/independent_verification.json','results/control_independent_verification.json','results/paired_media_verification.json',
              'evidence/visual_review.json','evidence/control_status_01.txt','evidence/delivery_record.json','evidence/control_delivery_record.json']
    record={'status':'NATIVE_TRACK_GAP_ASSOCIATION_DIAGNOSIS_AND_ONE_FACTOR_COST_CONTROL_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'jobs_completed':['130347','130348','130349'],
            'job_exit_codes':['0:0','0:0','0:0'],'full_history_replays':4,'tracker_updates_each_full_replay':2025,
            'six_step_short_replays':4,'signal_red_repeats':2,'controlled_short_signal':'GREEN','controlled_event_frame0':2675,
            'independent_cost_entries':51,'partial_assignments_enumerated':26,'independent_control_counter_paths':4,
            'native_control_centers':600,'new_long_seed26_predictions_before_after':[11,12],
            'other_event_timing_change_frame0':[3845,3840],'source_frames_hash_rechecked':625,
            'paired_videos_fully_decoded':3,'paired_video_frames_fully_decoded':625,'sheets_actually_viewed':6,'panels_actually_viewed':12,
            'local_links_checked':len(links),'diagnostic_archive_members':22,'control_archive_members':38,
            'original_confirmed12_candidate_preserved':True,'prior_four_model_results_preserved':True,'reference_drafts_preserved':True,
            'candidate_adopted':False,'old_clip_and_other_seed_regression_pending':True,'new_reference_final_scoring_eligible':False,
            'new_detector_forwards':0,'new_training_updates':0,'formal_scores_computed':False,'FPGA_execution_verified':False,'whole_goal_complete':False,
            'evidence_hashes':{r:sha(ROOT/r) for r in evidence},'retained_prior_review_sha256':sha(prior_root/'results/final_review.json'),
            'documents':[{'path':str(x.resolve()),'sha256':sha(x)} for x in docs],'rasters':rasters}
    path=ROOT/'results/final_review.json';assert not path.exists();path.write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['documents','evidence_hashes','rasters']}))
if __name__=='__main__':main()
