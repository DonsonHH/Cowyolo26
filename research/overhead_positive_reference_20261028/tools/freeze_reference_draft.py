"""Freeze a source-bound assistant visual draft that cannot be mistaken for scoring GT."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    witness=ROOT/'results/draft_witnesses_v2/manifest.json';w=load(witness);visual=ROOT/'evidence/focused_visual_review.json';v=load(visual)
    assert v['reference_count_provisional']==12 and v['manual_draft_eligible_for_final_scoring'] is False
    old=load(ROOT/'results/draft_witnesses/manifest.json')
    assert len(w['candidates'])==len(old['candidates'])==12
    review_ranges={'R01':[2650,2675],'R02':[2680,2700],'R03':[2690,2715],'R04':[2700,2725],
                   'R05':[2910,2935],'R06':[3355,3385],'R07':[3595,3635],'R08':[3680,3710],
                   'R09':[3820,3860],'R10':[3805,3835],'R11':[3990,4035],'R12':[5290,5335]}
    rows=[]
    for item,before in zip(w['candidates'],old['candidates']):
        ID=item['reference_ID'];assert ID==before['reference_ID']
        if ID not in ['R01','R02','R03','R04']:
            assert item['contact_sha256']==before['contact_sha256']
        A=[r for r in item['witnesses'] if r['region_hypothesis']=='A'];B=[r for r in item['witnesses'] if r['region_hypothesis']=='B']
        assert len(A)==len(B)==3 and max(r['frame0'] for r in A)<min(r['frame0'] for r in B)
        for triplet in [A,B]:assert [r['frame0'] for r in triplet]==list(range(triplet[0]['frame0'],triplet[0]['frame0']+15,5))
        for r in item['witnesses']:assert sha(ROOT/r['source_image'])==r['source_sha256']
        assert sha(ROOT/item['contact'])==item['contact_sha256']
        interval=review_ranges[ID]
        rows.append({'reference_ID':ID,'window':item['window'],'category':'cow','direction':'A->B','visual_description':item['description'],
                     'origin_evidence_frame0':[r['frame0'] for r in A],'destination_evidence_frame0':[r['frame0'] for r in B],
                     'destination_transition_review_frame0_interval':interval,'nominal_time_interval_s':[r/25 for r in interval],
                     'interval_is_a_review_target_not_formal_error_bound':True,'exact_event_frame0':None,'exact_event_time_s':None,
                     'witness_contact':item['contact'],'witness_contact_sha256':item['contact_sha256'],
                     'source_witnesses':item['witnesses'],'event_classification':'assistant_provisional_complete_downward_candidate',
                     'independently_human_accepted':False,'review_status':'pending_independent_review'})
    result={'status':'FROZEN_ASSISTANT_NATIVE_PIXEL_EVENT_DRAFT_NOT_FOR_FINAL_SCORING','created_UTC':datetime.now(timezone.utc).isoformat(),
            'source_sha256':load(ROOT/'protocol/selection_v1.json')['upstream_source_sha256'],'source_filename':'2023-08-17T13-25-38.mp4',
            'nominal_source_FPS':25,'frame_indexing':'0-based original decoded source frames','annotation_authority':'assistant_provisional_native_visual_review',
            'source_pixels_reviewed_before_new_model_predictions':True,'new_model_predictions_seen':False,
            'rules_path':'protocol/manual_reference_rules_v1.json','rules_sha256':sha(ROOT/'protocol/manual_reference_rules_v1.json'),
            'focus_protocol_sha256':sha(ROOT/'protocol/focused_review_v1.json'),'visual_review_sha256':sha(visual),
            'witness_manifest_sha256':sha(witness),'review_windows_frame0_halfopen':[[2375,4375],[5000,5625],[9625,10125]],
            'provisional_downward_candidates':12,'group_window_candidates':11,'late_window_candidates':1,'candidates':rows,
            'noncow_controls':[{'kind':'person','window':'group_passage','approximate_frames0':[2700,2825],'direction_visual':'downward'},
                               {'kind':'person','window':'person_control','approximate_frames0':[9825,9975],'direction_visual':'upward'}],
            'censored_or_ambiguous_items':[],'censoring_review_scope':'Selected candidate paths only; no full-frame annotation or certified whole-video census.',
            'all_individual_sample_frames_visually_reviewed':False,'independent_human_confirmation_received':False,
            'exact_event_timestamps_finalized':False,'eligible_for_final_scoring':False,
            'reason_scoring_blocked':'Independent acceptance and exact destination-stability times are not yet supplied; keep targeted time brackets and raw witnesses.',
            'original_user_confirmed12_clip_reference_unchanged':True,'this_new12_draft_is_not_user_confirmation':True,
            'FPGA_execution_verified':False,'whole_goal_complete':False}
    out=ROOT/'reference';out.mkdir(exist_ok=False)
    target=out/'assistant_event_draft_v1.json';target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    record={'reference_path':str(target),'sha256':sha(target),'source_sha256':result['source_sha256'],'authority':result['annotation_authority'],
            'provisional_candidates':12,'eligible_for_final_scoring':False,'exact_event_timestamps_finalized':False}
    (out/'freeze_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record),flush=True)
if __name__=='__main__':main()
