"""Verify the accepted human total, fixed candidate and camera-scope change."""
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import hashlib,json,re

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    reference_path=ROOT/'evidence/user_confirmation.json';reference=read(reference_path)
    assert reference['human_total_reference_accepted'] is True and reference['human_confirmed_total']==12
    assert reference['source_frame_interval_inclusive']==[8912,10873]
    assert '就是12头牛，已经确认无误了' in reference['user_statement_verbatim']
    assert '从正上方向下看牛' in reference['user_statement_verbatim']
    assert reference['per_event_frame_annotations_supplied'] is False and reference['blind_review_procedure_documented'] is False
    assert sha(PROJECT/reference['source_video_relative_path'])==reference['source_video_sha256']
    comparison=read(ROOT/'results/total_count_comparison.json');candidate=read(ROOT/'results/frozen_development_candidate.json')
    assert comparison['reference_sha256']==candidate['reference_sha256']==sha(reference_path)
    catalog_path=Path(candidate['catalog_path']);catalog=read(catalog_path)
    assert sha(catalog_path)==comparison['catalog_sha256']==candidate['catalog_sha256']=='26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac'
    assert len(catalog['conditions'])==len(comparison['all_conditions'])==29
    assert candidate['condition_id']=='confirmation_handoff_20261028/seed26' and candidate['selected_on_development_clip_after_feedback'] is True
    assert candidate['predicted_down']==candidate['human_total']==12 and candidate['absolute_total_error']==0
    assert sha(Path(candidate['checkpoint_path']))==candidate['checkpoint_sha256']=='51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74'
    upstream=[]
    for before,after in zip(catalog['conditions'],comparison['all_conditions']):
        assert before['condition_id']==after['condition_id']
        for base in ['events','summary','protocol']:
            if base+'_path' in before:
                path=Path(before[base+'_path']);assert sha(path)==before[base+'_sha256']
                upstream.append({'path':str(path),'sha256':before[base+'_sha256']})
        assert after['human_confirmed_down']==12 and after['predicted_down']==before['predicted_A_to_B']
        assert after['signed_total_error']==after['predicted_down']-12
        assert after['absolute_total_error']==abs(after['predicted_down']-12)
        assert after['total_matches_human']==(after['predicted_down']==12)
        assert after['event_F1_available'] is False
    main_rows=sorted(comparison['main_three_seeds'],key=lambda r:r['seed']);actual_counts=[]
    for r in main_rows:
        events=read(Path(r['events_path']));assert isinstance(events,list)
        down=[e for e in events if e['direction']=='A->B' and 8912<=e['source_frame']<=10873]
        assert all(abs(e['source_frame']/25-e['time_s'])<1e-9 for e in down)
        assert len(down)==r['predicted_down'];actual_counts.append(len(down))
    assert actual_counts==[12,11,11] and [r['absolute_total_error'] for r in main_rows]==[0,1,1]
    # Preserve the discarded branch as partial history; do not continue processing its pixels.
    archived=PROJECT/'mootrack_continuous_20261028';fetch=read(archived/'evidence/video_ranges/manifest.json')
    assert fetch['status']=='ALL_FIVE_FROZEN_CONTINUOUS_WINDOWS_FETCHED' and fetch['model_predictions_or_training'] is False
    prior_summaries=[read(archived/'results'/w['name']/'summary.json') for w in fetch['windows']]
    assert sum(s['decode_frames'] for s in prior_summaries)==570 and sum(s['render_frames'] for s in prior_summaries)==450
    assert len(prior_summaries)==5 and sum(len(s['videos']) for s in prior_summaries)==10
    docs=[ROOT/'人工确认12头与后续数据路线.md',ROOT/'Review与当前状态.md',archived/'分支归档说明.md',
          PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for p in docs:
        text=p.read_text(encoding='utf-8');assert '\ufffd' not in text
        for m in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',text):
            url=unquote(m[1] or m[2])
            if re.match(r'^[A-Za-z]:[/\\]',url):assert Path(url).exists(),url;links.append(url)
    for p in docs[-3:]:
        text=p.read_text(encoding='utf-8');assert '12头' in text and 'human_count_confirmation_20261028' in text and '普通' in text
    assert candidate['per_event_correctness_proven'] is False and candidate['FPGA_execution_verified'] is False
    result={'status':'HUMAN_TOTAL_12_ACCEPTED_DEVELOPMENT_CANDIDATE_AND_CAMERA_PIVOT_REVIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'reference_sha256':sha(reference_path),
            'comparison_sha256':sha(ROOT/'results/total_count_comparison.json'),
            'candidate_sha256':sha(ROOT/'results/frozen_development_candidate.json'),
            'human_confirmed_total':12,'human_total_reference_accepted':True,'current_clip_total_goal_achieved':True,
            'actual_main_prediction_events_recounted':actual_counts,'absolute_total_errors':[0,1,1],
            'current_usable_development_candidate':candidate['condition_id'],'all_conditions_compared':29,
            'historical_event_summary_protocol_hashes_rechecked':len(upstream),
            'historical_catalog_preserved_sha256':sha(catalog_path),'model_weights_unchanged':True,
            'source_events_promoted_to_reference':False,'per_event_F1_claimed':False,'blind_review_claimed':False,
            'discarded_fisheye_branch':'Archived after user requested ordinary directly-overhead cameras; partial visual review retained honestly',
            'discarded_branch_has_no_model_training_or_inference':True,'discarded_branch_browser_playback_claimed':False,
            'ordinary_overhead_video_priority':True,'source_clip_remains_development_data':True,
            'new_training_updates':0,'new_model_forwards':0,'FPGA_execution_verified':False,'local_links_checked':len(links),
            'documents':[{'path':str(p),'sha256':sha(p)} for p in docs],'upstream_records':upstream,
            'goal_turn_progress':'User-confirmed ground-truth total accepted, successful source candidate frozen and camera scope corrected',
            'next_priority':'New normal overhead sessions, suitable video annotations and subsequent real board joint inference',
            'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['documents','upstream_records']},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
