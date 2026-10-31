from pathlib import Path
from collections import Counter
import hashlib,json,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    c=load(ROOT/'results/frozen_prediction_catalog_v2.json');old=Path(c['previous_catalog_path'])
    assert sha(old)==c['previous_catalog_sha256'] and c['conditions'][:17]==load(old)['conditions']
    assert len(c['conditions'])==len({r['condition_id'] for r in c['conditions']})==23
    files={};eventrows=0
    for row in c['conditions']:
        for key in ['events','summary','protocol']:
            path=Path(row[key+'_path']);assert path.resolve().is_relative_to(PROJECT.resolve()) and sha(path)==row[key+'_sha256']
            files[str(path)]=sha(path)
        events=load(row['events_path']);counts=Counter()
        for e in events:
            assert type(e['source_frame']) is int and 8912<=e['source_frame']<=10873
            assert math.isfinite(e['time_s']) and e['time_s']==e['source_frame']/25 and e['direction'] in ['A->B','B->A']
            counts[e['direction']]+=1
        assert len(events)==row['predicted_events'] and counts['A->B']==row['predicted_A_to_B'] and counts['B->A']==row['predicted_B_to_A']
        assert row['source_sha256']==c['source_sha256'] and row['history_start']==0 and row['source_frame_scope']==[8912,10873]
        eventrows+=len(events)
    latest=c['conditions'][17:];assert [r['predicted_events'] for r in latest]==[11,12,10,11,11,11]
    for row in latest:
        contract=json.dumps(row['pipeline_contract'],sort_keys=True,separators=(',',':')).encode()
        assert hashlib.sha256(contract).hexdigest()==row['pipeline_contract_sha256']
        seed=row['seed'];weight=PROJECT/f'cows2021_adaptation_20261027/delivery/results/training/seed{seed}/weights/last.pt'
        assert sha(weight)==row['checkpoint_sha256']
    index={r['condition_id']:r for r in c['conditions']}
    for pair in c['paired_comparisons']:
        a=index[pair['baseline_condition_id']];b=index[pair['candidate_condition_id']]
        assert a['seed']==b['seed']==pair['seed'] and a['checkpoint_sha256']==b['checkpoint_sha256']
        assert a['pipeline_contract_sha256']!=b['pipeline_contract_sha256']
        added=Counter((e['source_frame'],e['track_id'],e['direction']) for e in load(b['events_path']))
        original=Counter((e['source_frame'],e['track_id'],e['direction']) for e in load(a['events_path']))
        assert not (original-added)
    for a in c['exact_prior_event_aliases'][3:]:
        path=Path(a['historical_events_path']);assert sha(path)==a['historical_events_sha256']
        assert load(path)==load(index[a['canonical_condition']]['events_path'])
    r={'status':'ALL23_CATALOG_CONDITIONS_INPUT_HASHES_AND_CURRENT_PAIRS_INDEPENDENTLY_VERIFIED',
       'catalog_sha256':sha(ROOT/'results/frozen_prediction_catalog_v2.json'),'conditions':23,'historical_unchanged':17,
       'current_paired_conditions':6,'pairs':3,'distinct_bound_artifact_files':len(files),'indexed_prediction_events':eventrows,
       'new_independent_reference_received':False,'actual_accuracy_computed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/catalog_verification.json';assert not target.exists();target.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
if __name__=='__main__':main()
