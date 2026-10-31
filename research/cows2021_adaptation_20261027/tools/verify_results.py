"""Independent file/data/training/event reconciliation; no model forward."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,functools,hashlib,json,math
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def replay(rows,ticks,fps):
    states={};byframe=defaultdict(list);events=[]
    for row in rows:byframe[int(row['source_frame'])].append(row)
    for frame in ticks:
        positions={int(r['track_id']):float(r['axis_position']) for r in byframe.get(frame,[])}
        for tid,state in states.items():
            if tid not in positions:state['candidate']=None;state['streak']=0
        for tid,p in positions.items():
            if not 0<=p<=1:continue
            s=states.setdefault(tid,{'origin':None,'candidate':None,'streak':0,'last':-1e30})
            if frame/fps-s['last']>2:s.update(origin=None,candidate=None,streak=0)
            s['last']=frame/fps;zone='A' if p<.4 else 'B' if p>.6 else None
            if zone is None:s.update(candidate=None,streak=0);continue
            s['streak']=s['streak']+1 if zone==s['candidate'] else 1;s['candidate']=zone
            if s['streak']>=3 and s['origin']!=zone:
                if s['origin'] is not None:events.append({'time_s':frame/fps,'track_id':tid,'direction':s['origin']+'->'+zone,'source_frame':frame})
                s['origin']=zone
    return events

def matching(reference,predicted):
    # DP over prediction index and used reference mask. Independent of SciPy.
    n=len(reference);assert n==6
    @functools.lru_cache(None)
    def solve(j,mask):
        if j==len(predicted):return (0,0.,())
        best=solve(j+1,mask)
        for i,r in enumerate(reference):
            delta=abs(float(r['time_s'])-float(predicted[j]['time_s']))
            if mask&(1<<i) or delta>2:continue
            count,error,pairs=solve(j+1,mask|(1<<i))
            candidate=(count+1,error+delta,((i,j),)+pairs)
            if (candidate[0],-candidate[1])>(best[0],-best[1]):best=candidate
        return best
    _,_,pairs=solve(0,0)
    correct=sum(reference[i]['direction']==predicted[j]['direction'] for i,j in pairs)
    return {'TP':correct,'FP':len(predicted)-correct,'FN':len(reference)-correct,
            'temporally_matched':len(pairs),'wrong_direction_matches':len(pairs)-correct}


def main():
    delivered=ROOT/'delivery'
    entries=json.loads((delivered/'delivery_manifest.json').read_text(encoding='utf-8'))
    assert entries and len({r['path'] for r in entries})==len(entries)
    for entry in entries:
        path=delivered/entry['path'];assert path.resolve().is_relative_to(delivered.resolve())
        assert path.is_file() and path.stat().st_size==entry['bytes'] and sha(path)==entry['sha256'],entry['path']
    pp=delivered/'protocol/detector_v1.json';protocol=json.loads(pp.read_text(encoding='utf-8'))
    assert sha(pp)==sha(ROOT/'protocol/detector_v1.json')
    assert protocol['seeds']==[26,27,28] and protocol['epochs']==10
    fetch_path=ROOT/'input/image_fetch_manifest.json';fetch=json.loads(fetch_path.read_text(encoding='utf-8'))
    assert protocol['source_image_fetch_manifest_sha256']==sha(fetch_path)
    assert len(fetch['items'])==8380 and Counter(r['development_role'] for r in fetch['items'])=={'train':6809,'validation':1571}
    expected={r['file_name']:r for r in fetch['items']}
    loader_path=delivered/'results/labels_v1/summary.json';loader=json.loads(loader_path.read_text(encoding='utf-8'))
    assert loader['status']=='DERIVED_LABELS_AND_REAL_ULTRALYTICS_LOADER_PASS'
    audit_relative=Path(loader['source_image_audit_path']).name
    image_summary_path=delivered/'results'/audit_relative/'summary.json'
    image_summary=json.loads(image_summary_path.read_text(encoding='utf-8'))
    assert sha(image_summary_path)==loader['source_image_audit_sha256']
    assert image_summary['decoded_images']==8380 and image_summary['decode_errors']==0
    assert image_summary['candidate_final_image_pixels_accessed'] is False
    assert image_summary['final_independent_test_certified'] is False
    decoded_path=image_summary_path.parent/'decoded_images.json'
    assert sha(decoded_path)==image_summary['decoded_images_sha256']
    decoded=json.loads(decoded_path.read_text(encoding='utf-8'))
    assert len(decoded)==8380 and {r['file_name'] for r in decoded}==set(expected)
    for record in decoded:
        assert all(record[k]==v for k,v in expected[record['file_name']].items())
        assert record['PIL_complete_decode_verified'] is True and record['OpenCV_complete_decode_verified'] is True
        assert record['width']==1280 and record['height']==720 and record['bytes']>0
    overlap=json.loads((image_summary_path.parent/'overlap.json').read_text(encoding='utf-8'))
    groups=overlap['same_bytes_groups']+overlap['same_RGB_groups']
    quarantine={name for group in groups if len(group['roles'])>1 for name in group['members']}
    assert quarantine==set(overlap['cross_development_role_exact_members_quarantined'])
    prepared_path=delivered/'results/labels_v1/prepared_image_label_manifest.json'
    assert sha(prepared_path)==loader['prepared_manifest_sha256']
    prepared=json.loads(prepared_path.read_text(encoding='utf-8'))
    assert {r['file_name'] for r in prepared}==set(expected)-quarantine
    assert len(prepared)==len(expected)-len(quarantine)
    geometry=defaultdict(list)
    for record in json.loads((ROOT/'input/derived_box_catalog.json').read_text(encoding='utf-8')):
        geometry[record['file_name']].append(record)
    loaded=Counter();roles=Counter()
    for record in prepared:
        name=record['file_name'];wanted=expected[name]
        assert all(record[k]==v for k,v in wanted.items())
        assert record['actual_split']==('train' if wanted['development_role']=='train' else 'val')
        original=sorted(geometry[name],key=lambda r:r['annotation_id'])
        lines=['0 '+' '.join(f'{v:.9f}' for v in row['yolo_class_cxcywh'][1:]) for row in original]
        text='\n'.join(lines)+'\n'
        assert hashlib.sha256(text.encode()).hexdigest()==record['label_sha256']
        values=np.asarray([list(map(float,line.split())) for line in lines],dtype=np.float32)
        assert np.array_equal(values,np.asarray(record['expected_float32_rows'],dtype=np.float32))
        assert [r['annotation_id'] for r in original]==record['published_annotation_IDs']
        roles[record['actual_split']]+=1;loaded[record['actual_split']]+=len(lines)
    for record in loader['loader_results']:
        assert record['images']==roles[record['split']] and record['actual_loaded_annotation_rows']==loaded[record['split']]
    train=delivered/'results/training'
    summary=json.loads((train/'summary.json').read_text(encoding='utf-8'))
    assert summary['status']=='ALL_THREE_COWS2021_SEEDS_10_EPOCHS_COMPLETE_FROZEN_BEFORE_VIDEO'
    assert summary['protocol_sha256']==sha(pp) and summary['data_roles']==dict(roles)
    freeze_path=train/'all_checkpoints_frozen_before_video.json';freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
    assert summary['freeze_sha256']==sha(freeze_path) and freeze['protocol_sha256']==sha(pp)
    assert freeze['prepared_manifest_sha256']==sha(prepared_path)
    assert freeze['source_Toros_or_candidate_final_forward_before_freeze'] is False and freeze['all_seeds_retained'] is True
    assert [r['seed'] for r in freeze['conditions']]==[26,27,28]
    input_audit=json.loads((train/'input_audit.json').read_text(encoding='utf-8'))
    assert input_audit['prepared_manifest_sha256']==sha(prepared_path) and input_audit['roles']==dict(roles)
    assert input_audit['label_loader_summary_sha256']==sha(loader_path) and input_audit['loaded_labels']==dict(loaded)
    assert input_audit['source_video_or_candidate_final_pixels_used'] is False
    smoke_path=delivered/'results/preflight.json';smoke=json.loads(smoke_path.read_text(encoding='utf-8'))
    assert input_audit['preflight_sha256']==sha(smoke_path)
    assert smoke['status']=='PASS_ACTUAL_TRAIN_LOADER_AND_TWO_DISCARDED_CUDA_UPDATES'
    assert smoke['formal_training_updates']==0 and len(smoke['loss_and_gradient_history'])==2
    assert smoke['smoke_weights_saved_or_used_for_formal_training'] is False
    assert smoke['source_weights_sha256']==protocol['source_weights_sha256']
    for condition in freeze['conditions']:
        seed=condition['seed'];folder=train/f'seed{seed}'
        assert sha(folder/'weights/last.pt')==condition['checkpoint_sha256']
        rows=list(csv.DictReader((folder/'results.csv').open()))
        assert len(rows)==10 and [int(r['epoch']) for r in rows]==list(range(1,11))
        assert all(math.isfinite(float(v)) for r in rows for v in r.values())
        assert sha(folder/'results.csv')==condition['training_csv_sha256']
        assert sha(folder/'args.yaml')==condition['effective_args_sha256']
        initial=json.loads((folder/'initial_state.json').read_text(encoding='utf-8'))
        assert initial['state_digest']==condition['initial_state_digest']
        assert initial['train_images']==roles['train'] and initial['validation_images']==roles['val']
        assert initial['batches_per_epoch']*10==condition['actual_training_batches']
        steps=json.loads((folder/'optimizer_step_batch_indices.json').read_text(encoding='utf-8'))
        assert sha(folder/'optimizer_step_batch_indices.json')==condition['optimizer_step_schedule_sha256']
        assert len(steps)==condition['actual_optimizer_steps'] and all(a<b for a,b in zip(steps,steps[1:]))
        for key,value in condition['last_epoch_validation'].items():assert value==float(rows[-1][key])
    inference_path=delivered/'results/inference'
    inference=json.loads((inference_path/'summary.json').read_text(encoding='utf-8'))
    assert inference['status']=='THREE_COWS2021_MODELS_SOURCE_AND_KNOWN_DIAGNOSTIC_COMPLETE'
    assert inference['training_freeze_sha256']==sha(freeze_path) and inference['protocol_sha256']==sha(pp)
    assert [r['seed'] for r in inference['conditions']]==[26,27,28]
    reference=json.loads((inference_path/'toros_reference_events.json').read_text(encoding='utf-8'))
    assert len(reference)==6
    checks=[]
    for condition in inference['conditions']:
        frozen=next(r for r in freeze['conditions'] if r['seed']==condition['seed'])
        assert condition['checkpoint_sha256']==frozen['checkpoint_sha256']
        folder=inference_path/condition['name']
        for scene in ['source','Toros']:
            trace=list(csv.DictReader((folder/f'{scene}_tracks.csv').open()))
            if scene=='source':trace=list(csv.DictReader((folder/'source_warmup_tracks.csv').open()))+trace
            ticks=range(0,10874,5) if scene=='source' else range(479)
            saved=json.loads((folder/f'{scene}_events.json').read_text(encoding='utf-8'))
            calculated=replay(trace,ticks,25 if scene=='source' else 30)
            if scene=='source':calculated=[r for r in calculated if r['source_frame']>=8912]
            assert saved==calculated,(condition['name'],scene)
            record={'condition':condition['name'],'scene':scene,'events':len(calculated),'state_replay':'PASS'}
            if scene=='Toros':
                metrics=matching(reference,calculated)
                assert all(condition['Toros_event_metrics'][k]==v for k,v in metrics.items())
                record.update(metrics)
            checks.append(record)
    assert len(checks)==6 and inference['source_count_accuracy'] is None
    result={'status':'DATA_TRAINING_FREEZE_AND_SIX_EVENT_REPLAYS_INDEPENDENTLY_VERIFIED',
            'delivery_manifest_files':len(entries),'protocol_sha256':sha(pp),'roles':dict(roles),
            'quarantined_cross_role_exact_images':len(quarantine),'labels':dict(loaded),
            'seeds':[26,27,28],'epochs_each':10,'checks':checks,
            'source_independent_accuracy_verified':False,'candidate_final_test_certified':False,
            'Z2_joint_execution_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/independent_verification.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
