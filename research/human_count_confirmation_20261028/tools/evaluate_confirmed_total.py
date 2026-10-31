"""Accept the user's confirmed clip total; do not synthesize per-event ground truth."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=ROOT/'results';out.mkdir(parents=True,exist_ok=False)
    reference_path=ROOT/'evidence/user_confirmation.json';reference=json.loads(reference_path.read_text(encoding='utf-8'))
    assert reference['human_confirmed_total']==12 and reference['human_total_reference_accepted']
    assert reference['source_frame_interval_inclusive']==[8912,10873] and reference['per_event_frame_annotations_supplied'] is False
    video=PROJECT/reference['source_video_relative_path'];assert sha(video)==reference['source_video_sha256']
    catalog_path=PROJECT/'lost_recovery_20261028/results/frozen_prediction_catalog_v4.json'
    assert sha(catalog_path)=='26bd4c43a1345e12d0806409229976fa158efab11cc31529ea1f4255a53df8ac'
    catalog=json.loads(catalog_path.read_text(encoding='utf-8'));assert len(catalog['conditions'])==29
    rows=[]
    for r in catalog['conditions']:
        events_path=Path(r['events_path']);assert sha(events_path)==r['events_sha256']
        predicted=r['predicted_A_to_B'];assert predicted>=0
        rows.append({'condition_id':r['condition_id'],'seed':r.get('seed'),'predicted_down':predicted,'human_confirmed_down':12,
                     'signed_total_error':predicted-12,'absolute_total_error':abs(predicted-12),
                     'total_matches_human':predicted==12,'events_path':str(events_path),'events_sha256':r['events_sha256'],
                     'event_F1_available':False,'single_clip_development_comparison':True})
    main_rows=sorted([r for r in rows if r['condition_id'].startswith('confirmation_handoff_20261028/')],key=lambda r:r['seed'])
    assert [r['predicted_down'] for r in main_rows]==[12,11,11]
    assert [r['absolute_total_error'] for r in main_rows]==[0,1,1]
    selected=next(r for r in catalog['conditions'] if r['condition_id']=='confirmation_handoff_20261028/seed26')
    checkpoint=PROJECT/'cows2021_adaptation_20261027/delivery/results/training/seed26/weights/last.pt'
    assert sha(checkpoint)==selected['checkpoint_sha256']=='51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74'
    release={'status':'DEVELOPMENT_CANDIDATE_FROZEN_AFTER_USER_TOTAL_CONFIRMATION','condition_id':selected['condition_id'],
             'checkpoint_path':str(checkpoint),'checkpoint_sha256':sha(checkpoint),'reference_path':str(reference_path),'reference_sha256':sha(reference_path),
             'catalog_path':str(catalog_path),'catalog_sha256':sha(catalog_path),'source_event_record':selected,
             'selected_on_development_clip_after_feedback':True,'human_total':12,'predicted_down':12,'absolute_total_error':0,
             'supports_claim':'The source development clip total matches the human-confirmed 12 complete downward passages.',
             'per_event_correctness_proven':False,'new_unseen_test_performed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    (out/'frozen_development_candidate.json').write_text(json.dumps(release,indent=2,ensure_ascii=False),encoding='utf-8')
    result={'status':'HUMAN_TOTAL_ACCEPTED_AND_ALL_29_FROZEN_CONDITIONS_COMPARED','reference_sha256':sha(reference_path),
            'catalog_sha256':sha(catalog_path),'total_scope':'Complete downward passages, orange ROI, frames 8912-10873 inclusive.',
            'human_total':12,'main_three_seeds':main_rows,'all_conditions':rows,
            'equal_total_conditions':[r['condition_id'] for r in rows if r['total_matches_human']],
            'equal_total_conditions_are_not_independent_replications':True,'current_clip_milestone_achieved':True,
            'event_precision_recall_F1_not_calculated':True,'historical_catalog_not_rewritten':True,
            'independent_final_test_or_FPGA_success_claimed':False,'whole_goal_complete':False}
    (out/'total_count_comparison.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['main_three_seeds','all_conditions','equal_total_conditions']},ensure_ascii=False),flush=True)
    print(json.dumps([{'seed':r['seed'],'prediction':r['predicted_down'],'absolute_error':r['absolute_total_error']} for r in main_rows]),flush=True)

if __name__=='__main__':main()
