from pathlib import Path
from collections import Counter
import copy,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'paired_event_intake_20261028/tools'))
from build_catalog import validate_row
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    oldpath=PROJECT/'paired_event_intake_20261028/results/frozen_prediction_catalog_v2.json';old=load(oldpath)
    assert len(old['conditions'])==23;out=copy.deepcopy(old);p=load(ROOT/'protocol/secondstage_v1.json');summary=load(ROOT/'delivery/results/summary.json')
    index={r['condition_id']:r for r in old['conditions']};aliases=out['exact_prior_event_aliases']
    for seed in [26,27,28]:
        baseline_id=f'confirmation_handoff_20261028/seed{seed}';baseline=index[baseline_id]
        c=next(c for c in summary['conditions'] if c['seed']==seed and c['variant']=='secondstage_iou')
        folder=ROOT/'delivery/results'/c['name'];cid=f'secondstage_iou_20261028/{c["name"]}'
        contract={**baseline['pipeline_contract'],'firststage_score_fusion':True,'secondstage_score_fusion':False,
           'secondstage_cost':'1-IoU','secondstage_threshold':.5,'lost_secondstage_eligible':False,
           'secondstage_override_module_sha256':p['candidate_module_sha256']}
        row={**baseline,'condition_id':cid,'title':f'Full640 5Hz seed{seed}: secondstage IoU + fixed confirmation handoff',
             'summary_path':str(ROOT/'delivery/results/summary.json'),'summary_sha256':sha(ROOT/'delivery/results/summary.json'),
             'protocol_path':str(ROOT/'protocol/secondstage_v1.json'),'protocol_sha256':sha(ROOT/'protocol/secondstage_v1.json'),
             'events_path':str(folder/'handoff_events.json'),'events_sha256':sha(folder/'handoff_events.json'),
             'pipeline_contract':contract,'pipeline_contract_sha256':hashlib.sha256(json.dumps(contract,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
             'predicted_A_to_B':c['predicted_down'],'predicted_B_to_A':c['predicted_up'],'predicted_events':c['predicted_down']+c['predicted_up']}
        out['conditions'].append(row)
        out['paired_comparisons'].append({'seed':seed,'baseline_condition_id':baseline_id,'candidate_condition_id':cid,
           'baseline_predicted_events':baseline['predicted_events'],'candidate_predicted_events':row['predicted_events'],
           'candidate_selection_did_not_use_independent_reference':True,'single_factor':'secondstage scorefusion removal'})
        previous=ROOT/f'delivery/results/installed_baseline_seed{seed}/handoff_events.json';assert load(previous)==load(baseline['events_path'])
        aliases.append({'historical_condition':f'secondstage_iou_20261028/installed_baseline_seed{seed}',
           'canonical_condition':baseline_id,'normalized_events_equal':True,'historical_events_path':str(previous),'historical_events_sha256':sha(previous),
           'reason':'Full baseline tracker/history and current confirmation counter reproduced exactly'})
    assert len(out['conditions'])==len({r['condition_id'] for r in out['conditions']})==26 and out['conditions'][:23]==old['conditions']
    for row in out['conditions']:validate_row(row)
    out.update(status='26_FROZEN_CONDITIONS_WITH_SECONDSTAGE_CONTROL_ALL_SEEDS_INDEXED',
       previous_catalog_path=str(oldpath),previous_catalog_sha256=sha(oldpath),historical_records_preserved=23,
       event_timing_equality_is_not_pipeline_equivalence=True,
       selection_rule='Preserve all23 previous conditions, append allthree pureIoU secondstage controls; keep adverse and unchanged event results.',
       source_count_accuracy_verified=False,new_reference_received=False,new_inference=False,whole_goal_complete=False)
    target=ROOT/'results/frozen_prediction_catalog_v3.json';assert not target.exists();target.write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf-8')
    fields=['condition_id','seed','predicted_A_to_B','predicted_B_to_A','predicted_events','checkpoint_sha256']
    with target.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in out['conditions'])
    fields=['name','seed','variant','predicted_down','predicted_up','confirmed_only_down','ROI_track_IDs','ROI_track_rows','ROI_tracked_frames','applied_low_stage_matches_all_history','applied_low_stage_matches_in_scope']
    with (ROOT/'results/all_conditions.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in summary['conditions'])
    print(json.dumps({'catalog_conditions':26,'preserved_conditions':23,'pairs':len(out['paired_comparisons']),'current_predictions':[c['predicted_down'] for c in summary['conditions'] if c['variant']=='secondstage_iou']}))
if __name__=='__main__':main()
