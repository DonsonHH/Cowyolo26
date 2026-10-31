from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=ROOT/'results/render_v2_local_verification.json';r=load(p);assert r['manual_visual_QA']=='PENDING'
audit=load(ROOT/'results/audit.json');q=load(ROOT/'protocol/render_v1.json')
negative=q['special_cases'][1];assert negative['GT_a']['ID']==7 and negative['GT_b']['ID']==16
assert negative['GT_a']['IoU']>.5 and negative['GT_b']['IoU']>.5 and not negative['sensitivity_same_GT']
assert not any(e['both_IDs_emit_event_in_episode'] for e in audit['episodes'])
backup=ROOT/'results/render_v2_local_verification_before_visual.json';assert not backup.exists();shutil.copyfile(p,backup)
r.update(manual_visual_QA='PASS',visual_evidence_files=[{'file':name,'sha256':sha(ROOT/'render_v2_delivery/results/figures_v2'/name)}
     for name in ['redundancy_diagnostics.png','all6_representatives.jpg','known_case_and_distinct_cow_counterexample.jpg','native_f120.jpg','native_f323.jpg','native_f345.jpg','native_f421.jpg']],
   native_frames_visually_inspected=4,representative_panels_visually_inspected=6,special_panels_visually_inspected=2,
   manual_observations=['The mainplot has complete titles, legends, axes and counts. No cut contact captions in layoutv2.',
    'Frame421 official representatives overlap one partially visible cow at the rightedge; they are partial-track diagnostic cases.',
    'Frame345 pilot representatives overlap the same central visible cow across allthree variants, not a new Lost-only issue.',
    'Frame120 pilot has overlapping predictions on one visible cow; its rawpair is also duplicated.',
    'Frame323 official has highoverlap boxes but different publisher IDs7 and16 and two neighbouring visible cows; threshold alone cannot decide identity.'],
   complete_physical_duplicate_rate_or_new_reference_established=False)
p.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({'visual_QA':'PASS','native_frames':4,'representative_panels':6,'special_panels':2,'data_or_predictions_changed':False}))
