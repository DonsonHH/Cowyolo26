"""Independent exposure reconstruction, paired step gates, and12event replays."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,runpy
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    delivery=ROOT/'delivery';manifest=json.loads((delivery/'delivery_manifest.json').read_text(encoding='utf-8'))
    for row in manifest:
        file=delivery/row['path'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256'],row['path']
    p=json.loads((delivery/'protocol/composition_v1.json').read_text(encoding='utf-8'))
    original=json.loads((BASE/'detector_training_20261027/delivery/results/training/manifest.json').read_text(encoding='utf-8'))
    old_by_name={Path(r['image']).name:r for r in original};data={}
    for arm in ['mixed','real_repeated']:
        rows=json.loads((delivery/'data'/arm/'slot_manifest.json').read_text(encoding='utf-8'))
        train=[r for r in rows if r['split']=='train'];val=[r for r in rows if r['split']=='val']
        assert len(train)==5913 and len(val)==370
        for row in rows:
            before=old_by_name[Path(row['original_image']).name]
            assert before['split']==row['split'] and before['sha256']==row['image_sha256']
            assert before['synthetic_by_readme']==row['synthetic']
        counts=Counter(r['original_image'] for r in train)
        assert Counter(counts.values())==({1:5913} if arm=='mixed' else {2:1875,3:721})
        if arm=='real_repeated':
            assert not any(r['synthetic'] for r in train)
            eligible=sorted([r for r in original if r['split']=='train' and not r['synthetic_by_readme']],
                            key=lambda r:hashlib.sha256(('real-only-exposure-v1:'+Path(r['image']).name).encode()).hexdigest())
            assert [r['original_image'] for r in train]==[r['image'] for r in eligible+eligible+eligible[:721]]
        data[arm]={'train_source_files':len(counts),'training_slots':len(train),'val_pairs':[(r['image_sha256'],r['label_sha256']) for r in val]}
    assert data['mixed']['val_pairs']==data['real_repeated']['val_pairs']
    freeze=json.loads((delivery/'results/all_models_frozen.json').read_text(encoding='utf-8'))
    assert freeze['status']=='SIX_MODELS_AND_PAIRED_STEP_GATES_FROZEN' and not freeze['source_or_Toros_inference_enabled_before_this_file']
    assert freeze['protocol_sha256']==sha(delivery/'protocol/composition_v1.json')
    paired=[]
    for seed in [26,27,28]:
        pair=[next(r for r in freeze['conditions'] if r['condition']['seed']==seed and r['condition']['arm']==arm) for arm in ['mixed','real_repeated']]
        assert pair[0]['initial_model_digest']==pair[1]['initial_model_digest']
        steps=[]
        for condition in pair:
            name=condition['condition']['name'];folder=delivery/'results/training'/name
            assert condition['epochs']==10 and condition['training_batches']==1850
            assert sha(folder/'weights/last.pt')==condition['checkpoint_sha256']
            history=list(csv.DictReader((folder/'results.csv').open()))
            assert [int(r['epoch']) for r in history]==list(range(1,11))
            steps.append(json.loads((folder/'optimizer_step_batch_indices.json').read_text(encoding='utf-8')))
            assert len(steps[-1])==condition['optimizer_steps'] and steps[-1]==sorted(set(steps[-1]))
            assert steps[-1][-1]<=1850 and steps[-1][0]>=1
        assert steps[0]==steps[1]
        paired.append({'seed':seed,'actual_batches_each':1850,'optimizer_steps_each':len(steps[0]),'step_schedule_and_initialisation_equal':True})
    helpers=runpy.run_path(str(BASE/'detector_training_20261027/tools/verify_results.py'))
    inference=delivery/'results/inference';summary=json.loads((inference/'summary.json').read_text(encoding='utf-8'))
    assert summary['training_freeze_sha256']==sha(delivery/'results/all_models_frozen.json')
    reference=json.loads((inference/'toros_reference_events.json').read_text(encoding='utf-8'))
    checked=[]
    for condition in summary['conditions']:
        dest=inference/condition['name']
        for scene in ['source','Toros']:
            rows=list(csv.DictReader((dest/f'{scene}_tracks.csv').open()))
            if scene=='source':rows=list(csv.DictReader((dest/'source_warmup_tracks.csv').open()))+rows
            events=helpers['replay'](rows,range(0,10874,5) if scene=='source' else range(479),25 if scene=='source' else 30)
            if scene=='source':events=[r for r in events if r['source_frame']>=8912]
            expected=json.loads((dest/f'{scene}_events.json').read_text(encoding='utf-8'));assert events==expected
            row={'condition':condition['name'],'scene':scene,'events':len(events),'independent_event_replay':'PASS'}
            if scene=='Toros':
                independent=helpers['matching'](reference,events)
                assert all(condition['Toros_event_metrics'][k]==v for k,v in independent.items());row.update(independent)
            checked.append(row)
    assert len(checked)==12
    result={'status':'DATA_EXPOSURE_PAIR_GATES_AND_TWELVE_EVENT_REPLAYS_PASS','manifest_files':len(manifest),
            'arms':[{k:v for k,v in r.items() if k!='val_pairs'} for r in data.values()],'paired_controls':paired,'event_checks':checked,
            'source_true_passage_accuracy_verified':False,'independent_final_generalisation_verified':False,'board_verified':False,'whole_goal_complete':False}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
