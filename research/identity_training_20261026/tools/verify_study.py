"""Recompute retrieval, calibration and checkpoint choice without Torch/scorer."""
from pathlib import Path
from collections import defaultdict,Counter
from PIL import Image
import hashlib,json,tarfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
record=json.loads((ROOT/'results/bundle_record.json').read_text());bundle=ROOT/'results/training_delivery.tar.gz'
assert bundle.stat().st_size==record['bytes']
digest=hashlib.sha256(bundle.read_bytes()).hexdigest();assert digest==record['sha256']
dest=ROOT/'delivery'
if not dest.exists():
    dest.mkdir()
    with tarfile.open(bundle) as tf:tf.extractall(dest,filter='data')
manifest=json.loads((dest/'delivery_manifest.json').read_text())
for row in manifest:
    path=(dest/row['path']).resolve();assert path.is_relative_to(dest.resolve())
    assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
for relative in ['protocol/identity_training_v1.json','tools/train_and_evaluate.py','tools/training_primitives.py','tools/audit_inputs.py','tools/verify_saved_models.py']:
    assert hashlib.sha256((ROOT/relative).read_bytes()).digest()==hashlib.sha256((dest/relative).read_bytes()).digest(),relative
p=json.loads((dest/'protocol/identity_training_v1.json').read_text());audit=json.loads((dest/'results/input_audit/summary.json').read_text())
images=json.loads((dest/'results/input_audit/manifest.json').read_text());pixels=defaultdict(set)
for row in images:
    with Image.open(dest/row['relative_path']) as im:
        im.load();im=im.convert('RGB');w,h=im.size
        key=hashlib.sha256(w.to_bytes(4,'big')+h.to_bytes(4,'big')+im.tobytes()).hexdigest()
    assert key==row['pixel_sha256'];pixels[key].add(row['split'])
assert all(len(splits)==1 for splits in pixels.values())
roles=audit['eligible_roles'];identity_list=[i for group in roles.values() for i in group]
assert len(identity_list)==len(set(identity_list))
study=dest/'results/study';summary=json.loads((study/'summary.json').read_text());index=json.loads((study/'feature_index.json').read_text())
freeze_path=study/'all_models_and_thresholds_frozen.json';freeze=json.loads(freeze_path.read_text())
assert hashlib.sha256(freeze_path.read_bytes()).hexdigest()==summary['final_freeze_sha256']
assert freeze['forbidden_evaluation_accesses_before_gate']==0 and freeze['evaluation_features_computed'] is False
access=json.loads((study/'image_access_log.json').read_text())
assert all(r['evaluation_gate_open'] for r in access if r['split'].startswith('evaluation'))

def predictions(gallery,query,gs,qs):
    labels=sorted({r['identity'] for r in gs});gallery_ids=[r['identity'] for r in gs]
    scores=np.stack([np.max(query.astype(float)@gallery[np.array(gallery_ids)==label].astype(float).T,axis=1) for label in labels],axis=1)
    rows=[]
    for entry,s in zip(qs,scores):
        j=int(np.argmax(s));rows.append({'identity':entry['identity'],'predicted_id':labels[j],'is_known':entry['identity'] in labels,'similarity':float(s[j]),'relative_path':entry['relative_path']})
    return rows

def calibrate(rows):
    grouped=defaultdict(list)
    for r in rows:grouped[r['similarity']].append(r)
    total_unknown=sum(not r['is_known'] for r in rows);assert total_unknown>0
    best=(0,0,float(np.nextafter(max(grouped),np.inf)));c=w=u=0
    for score,group in sorted(grouped.items(),reverse=True):
        for r in group:
            if not r['is_known']:u+=1
            elif r['identity']==r['predicted_id']:c+=1
            else:w+=1
        candidate=(c,-w,score)
        if u/total_unknown<=.05+1e-12 and candidate>best:best=candidate
    return best[2]

def count(rows,tau):
    counts=Counter();perid=defaultdict(Counter)
    for r in rows:
        accepted=r['similarity']>=tau;known=r['is_known'];identity=r['identity']
        counts['known_queries' if known else 'unknown_queries']+=1;perid[identity]['N']+=1
        if known:
            counts['known_closed_top1_correct']+=r['identity']==r['predicted_id'];perid[identity]['top1']+=r['identity']==r['predicted_id']
            outcome='known_rejected_U' if not accepted else 'known_correct_accepted_C' if r['identity']==r['predicted_id'] else 'known_wrong_accepted_W'
            counts[outcome]+=1;perid[identity][outcome]+=1
        else:counts['unknown_false_accepts']+=accepted;perid[identity]['unknown_false_accepts']+=accepted
    keys=['known_queries','unknown_queries','known_closed_top1_correct','known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']
    return {key:int(counts[key]) for key in keys},perid

verified=[];outcomes={}
for condition in summary['conditions']:
    name=condition['name'];folder=study/name
    checkpoint=dest/'models/mobilenet_v3_small-047dcff4.pth' if condition['seed'] is None else folder/'best_encoder.pt'
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==condition['checkpoint_sha256']
    if condition['seed'] is not None:
        history=json.loads((folder/'training_history.json').read_text())
        assert len(history)==p['optimisation']['epochs'] and history[-1]['updates']==300
        chosen=max(history,key=lambda r:(r['validation_C'],-r['validation_W'],r['validation_top1'],-r['epoch']))
        assert chosen['epoch']==condition['selected_epoch']
    val=np.load(folder/'validation_embeddings.npz');ev=np.load(folder/'evaluation_embeddings.npz')
    calrows=predictions(val['gallery'],val['query'],index['validation_gallery'],index['validation_query'])
    tau=calibrate(calrows);assert abs(tau-condition['threshold']['threshold'])<1e-12
    rows=predictions(ev['gallery'],ev['query'],index['evaluation_gallery'],index['evaluation_query'])
    saved=json.loads((folder/'evaluation_predictions.json').read_text())
    for r,s in zip(rows,saved):
        assert r['relative_path']==s['relative_path'] and r['predicted_id']==s['predicted_id']
        assert abs(r['similarity']-s['similarity'])<1e-12
    metrics,perid=count(rows,condition['threshold']['threshold'])
    assert all(condition['evaluation'][key]==value for key,value in metrics.items())
    verified.append({'condition':name,'seed':condition['seed'],'selected_epoch':condition.get('selected_epoch'),
                     'threshold':condition['threshold']['threshold'],'counts':metrics,'independent_recalculation':'PASS'})
    outcomes[name]=perid

# Pair on actual held-out identities and average seeds before resampling IDs.
rng=np.random.default_rng(26);paired={}
baseline=outcomes['B_letterbox_frozen'];trained=[outcomes[r['condition']] for r in verified if r['seed'] is not None]
for role,key in [('evaluation_registered_ids','known_correct_accepted_C'),('evaluation_unknown_ids','unknown_false_accepts')]:
    ids=roles[role];differences=[]
    for identity in ids:
        b=baseline[identity][key]/baseline[identity]['N']
        c=np.mean([values[identity][key]/values[identity]['N'] for values in trained])
        differences.append(float(c-b))
    bootstrap=[float(rng.choice(differences,len(differences),replace=True).mean()) for _ in range(2000)]
    paired[role]={'metric':key,'identities':ids,'per_identity_seed_mean_minus_B':differences,
                  'mean_difference':float(np.mean(differences)),'percentile_95_identity_bootstrap_interval':np.quantile(bootstrap,[.025,.975]).tolist(),
                  'scope':'Three seeds averaged within each identity; independent units remain the held-out identities'}
reload=json.loads((dest/'results/checkpoint_verification/summary.json').read_text());assert reload['status']=='PASS' and len(reload['checks'])==10
report={'status':'PASS','bundle_sha256':digest,'manifest_files':len(manifest),'decoded_images':len(images),
        'identities_by_role':audit['identities_by_role'],'no_identity_role_overlap':True,'no_cross_split_pixel_duplicates':True,
        'no_evaluation_image_forward_before_freeze':True,'conditions':verified,'paired_B_to_C_analysis':paired,
        'checkpoint_reload_cpu_gpu_validation_agreement':'PASS','whole_project_complete':False,
        'scope':'Independent integrity, checkpoint-selection and stored-feature scoring; not another training run or field validation'}
(ROOT/'results/independent_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
