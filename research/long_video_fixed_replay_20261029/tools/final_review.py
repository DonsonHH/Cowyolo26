"""Bind actual predictions, delivered files, native visual evidence and report links."""
from pathlib import Path
from PIL import Image
from urllib.parse import unquote
from datetime import datetime,timezone
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=load(ROOT/'protocol/replay_v1.json');s=load(ROOT/'delivery/results/summary.json')
    v=load(ROOT/'results/independent_verification.json');m=load(ROOT/'results/media_verification.json')
    case=load(ROOT/'results/case_diagnosis.json');visual=load(ROOT/'evidence/visual_review.json')
    delivery=load(ROOT/'evidence/delivery_record.json');status=(ROOT/'evidence/status_04.txt').read_text(encoding='utf-8')
    assert delivery['job_id']=='130345' and delivery['sacct_state']=='COMPLETED' and delivery['sacct_exit_code']=='0:0'
    assert re.search(r'130345\s+long-video-fixed-replay\s+4gpu\s+COMPLETED\s+0:0\s+00:09:14',status)
    assert (ROOT/'evidence/replay_130345.err').stat().st_size==0
    stdout=(ROOT/'evidence/replay_130345.out').read_text(encoding='utf-8');assert 'Traceback' not in stdout
    last=json.loads(stdout.splitlines()[-1]);assert all(last[k]==delivery[k] for k in ['files','archive_bytes','archive_sha256'])
    assert sha(ROOT/'evidence/actual_remote_replay.py')==sha(ROOT/'tools/replay.py')
    archive=ROOT/'replay_delivery.tar.gz';assert archive.stat().st_size==delivery['archive_bytes'] and sha(archive)==delivery['archive_sha256']
    manifest=load(ROOT/'delivery/delivery_manifest.json')['files']
    for row in manifest:
        path=ROOT/'delivery'/row['file'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
    assert len(manifest)==89 and delivery['files']==90
    assert sha(ROOT/'protocol/replay_v1.json')==s['protocol_sha256']=='90bac31ca2224544a1ca62c3a7046842c1c744b584e976d1a4b745d1c9b4bd0a'
    assert s['model_forwards']==v['observation_ticks']==8100 and s['counter_paths']==8
    assert sum(x['raw_boxes_inverse_verified'] for x in v['checks'])==4808 and v['native_ROI_centers']==731
    assert sum(x['accepted_tentative_observations'] for x in v['checks'])==42
    totals={};baselines={};scopes=[]
    for spec,model,check in zip(p['models'],s['models'],v['checks']):
        assert spec['name']==model['model']==check['model'] and model['checkpoint_sha256']==spec['sha256']
        assert model['source_sha256']==p['source_sha256'] and model['restoration_seam_checks']==2025
        assert model['maximum_inverse_error']<=.0005 and model['source_history_start0']==0
        if spec['seed'] is not None:
            checkpoint=PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{spec["seed"]}/weights/last.pt'
            assert sha(checkpoint)==spec['sha256']
        name=spec['name'];totals[name]=baselines[name]=0
        for scope in model['all_scope_events']:
            c={r['counter']:r for r in scope['counter_paths']};assert all(r['predicted_up']==0 for r in c.values())
            totals[name]+=c['confirmation_handoff']['predicted_down'];baselines[name]+=c['confirmed_only']['predicted_down']
            if scope['window']=='person_control':assert all(r['predicted_down']==0 for r in c.values())
            scopes.append({'model':name,'window':scope['window'],'confirmed_only_down':c['confirmed_only']['predicted_down'],
                           'handoff_down':c['confirmation_handoff']['predicted_down'],'up':0})
        assert totals[name]==model['handoff_events_all_history'] and baselines[name]==model['confirmed_events_all_history']
    assert list(totals.values())==[0,11,12,12] and list(baselines.values())==[0,11,11,12]
    assert m['movie_count']==12 and m['decoded_frames']==12500 and m['case_panels']==36
    for row in m['media']:assert row['strict_decode']=='PASS' and row['fps']==25 and sha(Path(row['path']))==row['sha256']
    assert len(visual['sheets'])==11 and sum(r['panels_viewed'] for r in visual['sheets'])==44
    for row in visual['sheets']:assert row['actual_visual_review']=='PASS' and sha(Path(row['path']))==row['sha256']
    rasters=[]
    for path in sorted((ROOT/'results').rglob('*')):
        if path.suffix.lower() not in ['.jpg','.png']:continue
        with Image.open(path) as im:im.verify()
        rasters.append({'path':str(path.resolve()),'sha256':sha(path)})
    assert len(rasters)==55
    assert case['seed26_fragment_IDs']==[19,23] and case['seed26_three_missing_sample_frames']==[2650,2655,2660]
    assert case['seed27_counter_only_event_added']=={'frame0':2720,'track_ID':18,'direction':'A->B'}
    retained={
      'human_count_confirmation_20261028/evidence/user_confirmation.json':'fe8a895cd6ac71815ff8e2f6ad8d932a6453c41971b6b7a18ea9c2f743dd0f9f',
      'human_count_confirmation_20261028/results/frozen_development_candidate.json':'5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b',
      'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json':'26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac',
      'overhead_positive_reference_20261028/reference/assistant_event_draft_v1.json':'35a6e0d5b4454cc2a6e6057c750f84cd6cf5d02f5d3fc73c4c1683c80b149bb7',
      'event_timing_refinement_20261029/reference/assistant_event_timing_v2.json':'188079a8754c495485c284b8e0a29519181100033166fe953e9f7547c600dc6a',
      'overhead_long_session_20261028/input/2023-08-17T13-25-38.mp4':'8210a5bf206dd7f2356bc3d4653b439ab6de12ccfdc8209fe301ac7f02807058'}
    for path,digest in retained.items():assert sha(PROJECT/path)==digest
    accepted=load(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json')
    assert accepted['human_total']==accepted['predicted_down']==12 and accepted['absolute_total_error']==0
    assert load(PROJECT/'event_timing_refinement_20261029/reference/assistant_event_timing_v2.json')['eligible_for_final_scoring'] is False
    documents=[ROOT/'计划与验收.md',ROOT/'普通俯视长片四模型回放与研究决策.md',ROOT/'Review与当前状态.md',
               PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for path in documents:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text and '\r\r' not in text
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):
                line=re.match(r'^(.*):(\d+)$',url);target=Path(line[1] if line else url);assert target.exists(),target
                links.append({'document':str(path.resolve()),'target':str(target)})
    evidence=['protocol/replay_v1.json','results/independent_verification.json','results/media_verification.json',
              'results/case_diagnosis.json','evidence/visual_review.json','evidence/delivery_record.json',
              'evidence/status_04.txt','evidence/replay_130345.out','evidence/replay_130345.err','evidence/actual_remote_replay.py']
    result={'status':'FOUR_FROZEN_MODELS_NATIVE_LONG_VIDEO_REPLAY_AND_CASE_DIAGNOSIS_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':'130345','job_state':'COMPLETED','job_exit_code':'0:0',
            'manifest_files':89,'archive_members':90,'new_model_forwards':8100,'independent_counter_paths':8,
            'counter_update_ticks':16200,'raw_boxes_inverse_checked':4808,'native_ROI_centers_checked':731,
            'handoff_down_predictions':totals,'confirmed_only_down_predictions':baselines,'all_scopes':scopes,
            'movies_fully_decoded':12,'movie_frames_fully_decoded':12500,'raster_files_verified':55,
            'actual_sheets_viewed':11,'actual_panels_viewed':44,'local_links_checked':len(links),
            'new_training_updates':0,'new_Slurm_jobs':1,'new_different_clip_user_confirmed12_preserved':True,
            'current_29_condition_catalog_unchanged':True,'new_clip_references_unchanged':True,
            'new_reference_authority':'assistant_provisional_native_visual_review','new_reference_final_scoring_eligible':False,
            'formal_accuracy_or_F1_computed':False,'human_full_movie_playback_claimed':False,
            'source_and_retained_artifact_hashes':retained,'evidence_hashes':{x:sha(ROOT/x) for x in evidence},
            'documents':[{'path':str(x.resolve()),'sha256':sha(x)} for x in documents],
            'rasters':rasters,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/final_review.json';assert not target.exists();target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['documents','rasters','evidence_hashes','source_and_retained_artifact_hashes','all_scopes']}))
if __name__=='__main__':main()
