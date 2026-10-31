"""Independent gallery and rejection recomputation from saved feature vectors.

Does not import the original metric/calibration implementation or Torch.
"""
from pathlib import Path
from collections import defaultdict,Counter
from PIL import Image
import hashlib,json,tarfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
bundle=ROOT/'results/identity_delivery.tar.gz'
assert bundle.stat().st_size==29035236
bundle_hash=hashlib.sha256(bundle.read_bytes()).hexdigest()
assert bundle_hash=='e420ac9c2bf8ea233484ef551fb13b6427886828ead2892a6007e91919928364'
dest=ROOT/'delivery'
if not dest.exists():
    dest.mkdir()
    with tarfile.open(bundle) as tf:tf.extractall(dest,filter='data')
files=json.loads((dest/'delivery_manifest.json').read_text())
for row in files:
    p=(dest/row['path']).resolve();assert p.is_relative_to(dest.resolve())
    assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
for relative in ['protocol/identity_pilot_v1.json','protocol/aggregation_v1.json','tools/run_identity_baseline.py','tools/aggregate_identity.py','tools/identity_metrics.py']:
    assert hashlib.sha256((ROOT/relative).read_bytes()).digest()==hashlib.sha256((dest/relative).read_bytes()).digest()
manifest=json.loads((dest/'catalog/image_manifest.json').read_text())
decoded=0;pixel_splits=defaultdict(set)
for row in manifest:
    with Image.open(dest/row['relative_path']) as im:
        im.load();im=im.convert('RGB');w,h=im.size
        digest=hashlib.sha256(w.to_bytes(4,'big')+h.to_bytes(4,'big')+im.tobytes()).hexdigest()
        pixel_splits[digest].add(row['split']);decoded+=1
assert all(len(x)==1 for x in pixel_splits.values())
index=json.loads((dest/'results/embedding_baseline/embedding_index.json').read_text())
vectors=np.load(dest/'results/embedding_baseline/embeddings.npz')
gallery=vectors['gallery'].astype(float)
assert np.max(np.abs(np.linalg.norm(gallery,axis=1)-1))<1e-5
gallery_ids=np.array([r['identity'] for r in index['gallery']])
identities=sorted(set(gallery_ids));known=set(identities)
protocol=json.loads((dest/'protocol/identity_pilot_v1.json').read_text())
assert not(set(protocol['validation_unknown_ids'])&set(protocol['evaluation_unknown_ids']))
assert not (known&set(protocol['validation_unknown_ids'])) and not (known&set(protocol['evaluation_unknown_ids']))

def predict(vectors,entries):
    scores=np.stack([np.max(vectors.astype(float)@gallery[gallery_ids==identity].T,axis=1) for identity in identities],axis=1)
    result=[]
    for r,v in zip(entries,scores):
        j=int(np.argmax(v));result.append({**r,'is_known':r['identity'] in known,'predicted_id':identities[j],'similarity':float(v[j])})
    return result

def threshold(rows):
    # Traverse descending score groups. Compare feasible acceptance sets directly.
    groups=defaultdict(list)
    for row in rows:groups[row['similarity']].append(row)
    total_unknown=sum(not r['is_known'] for r in rows)
    assert total_unknown
    c=w=unknown=0;best=(0,0,float(np.nextafter(max(groups),np.inf)))
    best_tau=best[2]
    for score,group in sorted(groups.items(),reverse=True):
        c+=sum(r['is_known'] and r['predicted_id']==r['identity'] for r in group)
        w+=sum(r['is_known'] and r['predicted_id']!=r['identity'] for r in group)
        unknown+=sum(not r['is_known'] for r in group)
        candidate=(c,-w,score)
        if unknown/total_unknown<=.05+1e-12 and candidate>best:best=candidate;best_tau=score
    return best_tau

def counts(rows,tau):
    counts=Counter()
    for r in rows:
        accept=r['similarity']>=tau
        if r['is_known']:
            counts['known_queries']+=1
            counts['known_closed_top1_correct']+=r['identity']==r['predicted_id']
            label='known_rejected_U' if not accept else 'known_correct_accepted_C' if r['identity']==r['predicted_id'] else 'known_wrong_accepted_W'
            counts[label]+=1
        else:
            counts['unknown_queries']+=1;counts['unknown_false_accepts']+=accept
    return {k:int(counts[k]) for k in ['known_queries','unknown_queries','known_closed_top1_correct','known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']}

base=dest/'results/embedding_baseline';expected=json.loads((base/'summary.json').read_text())
cal=predict(vectors['calibration'],index['calibration']);evaluation=predict(vectors['evaluation'],index['evaluation'])
tau=threshold(cal)
assert abs(tau-expected['threshold'])<1e-12
for split,rows in [('calibration',cal),('evaluation',evaluation)]:
    saved=json.loads((base/f'{split}_scores.json').read_text())
    for p,q in zip(rows,saved):
        assert p['relative_path']==q['relative_path'] and p['predicted_id']==q['predicted_id']
        assert abs(p['similarity']-q['similarity'])<1e-12
    result=counts(rows,tau)
    assert all(value==expected[split][key] for key,value in result.items())

aggregation=json.loads((dest/'results/group_aggregation/summary.json').read_text())
group_results=[]
for condition in aggregation['conditions']:
    method=condition['method'];predictions={}
    for split in ['calibration','evaluation']:
        grouped=defaultdict(list)
        for i,row in enumerate(index[split]):grouped[row['identity']].append((row['relative_path'],i,row))
        group_vectors=[];entries=[]
        for identity,rows in sorted(grouped.items()):
            rows.sort();v=vectors[split][rows[0][1]].astype(float) if method=='single_first' else vectors[split][[r[1] for r in rows]].astype(float).mean(0)
            v=v/np.linalg.norm(v);group_vectors.append(v);entries.append(rows[0][2])
        predictions[split]=predict(np.array(group_vectors),entries)
    group_tau=threshold(predictions['calibration'])
    assert abs(group_tau-condition['threshold']['threshold'])<1e-12
    result=counts(predictions['evaluation'],group_tau)
    assert all(value==condition['evaluation'][key] for key,value in result.items())
    group_results.append({'method':method,'threshold':group_tau,'evaluation_counts':result,'verification':'PASS'})

# A zero-error cluster bootstrap can give [0,0] although population error is
# uncertain. Preserve the empirical result and provide its finite-sample bound.
bound=1-.05**(1/10)
statistics={'issue':'The five-image aggregation observed zero accepts among10 unknown identity groups; the empirical percentile bootstrap is degenerate at [0,0]. It does not bound future error at0.',
            'zero_false_accepts':0,'unknown_identity_groups':10,'one_sided_95_binomial_upper_bound':bound,
            'assumption':'Independent Bernoulli identity-group samples; descriptive small-cohort bound, not farm-wide guarantee',
            'recommendation':'Report 0/10 and sample size with this limit; do not use the zero-width bootstrap as a performance guarantee'}
(ROOT/'results/statistical_review.json').write_text(json.dumps(statistics,indent=2))
report={'status':'PASS','bundle_sha256':bundle_hash,'manifest_files':len(files),'decoded_images':decoded,'exact_pixel_cross_split_duplicates':0,
        'score_and_threshold_independent_recalculation':'PASS','image_evaluation_counts':counts(evaluation,tau),
        'aggregation':group_results,'statistical_boundary_review':statistics,
        'scope':'Independent integrity and gallery/calibration arithmetic; this does not independently reproduce the neural encoder or establish field performance'}
(ROOT/'results/independent_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
