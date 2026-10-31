from pathlib import Path
import copy,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'paired_event_intake_20261028/tools'))
from build_catalog import validate_row
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    oldpath=PROJECT/'secondstage_iou_20261028/results/frozen_prediction_catalog_v3.json';old=load(oldpath);out=copy.deepcopy(old)
    assert len(old['conditions'])==26;index={r['condition_id']:r for r in old['conditions']};p=load(ROOT/'protocol/lost_v1.json');summary=load(ROOT/'delivery/results/summary.json')
    for seed in [26,27,28]:
        baseline_id=f'secondstage_iou_20261028/secondstage_iou_seed{seed}';a=index[baseline_id]
        c=next(c for c in summary['conditions'] if c['seed']==seed and c['variant']=='allow_lost_iou');folder=ROOT/'delivery/results'/c['name']
        cid=f'lost_recovery_20261028/{c["name"]}';contract={**a['pipeline_contract'],'lost_secondstage_eligible':True,
            'lost_eligibility_module_sha256':p['candidate_module_sha256'],'track_buffer':30,'additional_motion_or_age_gate':False}
        row={**a,'condition_id':cid,'title':f'Full640 5Hz seed{seed}: low-score Lost eligibility + fixed IoU/handoff',
           'summary_path':str(ROOT/'delivery/results/summary.json'),'summary_sha256':sha(ROOT/'delivery/results/summary.json'),
           'protocol_path':str(ROOT/'protocol/lost_v1.json'),'protocol_sha256':sha(ROOT/'protocol/lost_v1.json'),
           'events_path':str(folder/'handoff_events.json'),'events_sha256':sha(folder/'handoff_events.json'),
           'pipeline_contract':contract,'pipeline_contract_sha256':hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
           'predicted_A_to_B':c['predicted_down'],'predicted_B_to_A':c['predicted_up'],'predicted_events':c['predicted_down']+c['predicted_up']}
        out['conditions'].append(row);out['paired_comparisons'].append({'seed':seed,'baseline_condition_id':baseline_id,
            'candidate_condition_id':cid,'baseline_predicted_events':a['predicted_events'],'candidate_predicted_events':row['predicted_events'],
            'candidate_selection_did_not_use_independent_reference':True,'single_factor':'Lost eligibility in fixed pure-IoU secondstage'})
        prior=ROOT/f'delivery/results/active_only_iou_seed{seed}/handoff_events.json';assert load(prior)==load(a['events_path'])
        out['exact_prior_event_aliases'].append({'historical_condition':f'lost_recovery_20261028/active_only_iou_seed{seed}',
            'canonical_condition':baseline_id,'normalized_events_equal':True,'historical_events_path':str(prior),'historical_events_sha256':sha(prior),
            'reason':'Exact full baseline regression including both counters and native tracker outputs'})
    assert len(out['conditions'])==len({r['condition_id'] for r in out['conditions']})==29 and out['conditions'][:26]==old['conditions']
    for r in out['conditions']:validate_row(r)
    out.update(status='29_FROZEN_CONDITIONS_WITH_LOST_ELIGIBILITY_CONTROL_ALL_SEEDS_INDEXED',
       previous_catalog_path=str(oldpath),previous_catalog_sha256=sha(oldpath),historical_records_preserved=26,
       selection_rule='Preserve all26 earlier records; append allthree Lost eligibility controls, including unchanged events.',
       source_count_accuracy_verified=False,new_reference_received=False,new_inference=False,whole_goal_complete=False)
    path=ROOT/'results/frozen_prediction_catalog_v4.json';assert not path.exists();path.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    fields=['condition_id','seed','predicted_A_to_B','predicted_B_to_A','predicted_events','checkpoint_sha256']
    with path.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in out['conditions'])
    fields=['name','seed','variant','predicted_down','predicted_up','confirmed_only_down','ROI_track_IDs','ROI_track_rows','ROI_tracked_frames','low_matches_all_history','lost_recoveries_all_history','lost_recoveries_in_scope','maximum_lost_recovery_gap_frames']
    with (ROOT/'results/all_conditions.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows({k:r[k] for k in fields} for r in summary['conditions'])
    print(json.dumps({'conditions':29,'preserved':26,'pairs':len(out['paired_comparisons'])}))
if __name__=='__main__':main()
