"""Known-identity retrieval and unknown-rejection accounting for a frozen gallery."""
import numpy as np

def calibrate_threshold(scores, predictions, true_ids, known_flags, maximum_unknown_far=.05):
    scores=np.asarray(scores,dtype=float);known=np.asarray(known_flags,dtype=bool)
    if not len(scores) or not np.isfinite(scores).all():raise ValueError('Finite calibration scores required')
    if not known.any() or known.all():raise ValueError('Both known and unknown calibration queries required')
    if not 0<=maximum_unknown_far<=1:raise ValueError('Invalid false-acceptance target')
    correct=np.asarray(predictions)==np.asarray(true_ids)
    candidates=list(np.unique(scores))+[float(np.nextafter(scores.max(),np.inf))]
    best=None
    for threshold in candidates:
        accepted=scores>=threshold
        unknown_accepts=int((accepted&~known).sum())
        if unknown_accepts/(~known).sum()>maximum_unknown_far+1e-12:continue
        c=int((accepted&known&correct).sum());w=int((accepted&known&~correct).sum())
        choice=((c,-w,float(threshold)),{'threshold':float(threshold),'calibration_known_correct_accepted':c,
                'calibration_known_wrong_accepted':w,'calibration_unknown_false_accepts':unknown_accepts,
                'calibration_unknown_queries':int((~known).sum()),'calibration_unknown_far':float(unknown_accepts/(~known).sum()),
                'selection':'Max correctly accepted known subject to empirical unknown FAR<=0.05; ties min known wrong accepts then higher threshold'})
        if best is None or choice[0]>best[0]:best=choice
    assert best is not None
    return best[1]

def summarise(rows):
    known=[r for r in rows if r['is_known']];unknown=[r for r in rows if not r['is_known']]
    def ratio(a,b):return a/b if b else None
    c=sum(r['accepted'] and r['predicted_id']==r['identity'] for r in known)
    w=sum(r['accepted'] and r['predicted_id']!=r['identity'] for r in known)
    u=sum(not r['accepted'] for r in known);false_unknown=sum(r['accepted'] for r in unknown)
    assert c+w+u==len(known)
    groups={identity:[r for r in rows if r['identity']==identity] for identity in sorted({r['identity'] for r in rows})}
    perid=[]
    for identity,g in groups.items():
        known_id=g[0]['is_known'];assert all(r['is_known']==known_id for r in g)
        perid.append({'identity':identity,'is_known':known_id,'queries':len(g),
                      'closed_top1_accuracy':ratio(sum(r['predicted_id']==identity for r in g),len(g)) if known_id else None,
                      'correct_accepted_rate':ratio(sum(r['accepted'] and r['predicted_id']==identity for r in g),len(g)) if known_id else None,
                      'false_accept_rate':ratio(sum(r['accepted'] for r in g),len(g)) if not known_id else None})
    result={'known_queries':len(known),'unknown_queries':len(unknown),'known_correct_accepted_C':c,
            'known_wrong_accepted_W':w,'known_rejected_U':u,'query_missing_M':0,
            'known_closed_top1_correct':sum(r['predicted_id']==r['identity'] for r in known),
            'known_closed_top1_accuracy':ratio(sum(r['predicted_id']==r['identity'] for r in known),len(known)),
            'known_correct_accepted_rate':ratio(c,len(known)),'known_wrong_accepted_rate':ratio(w,len(known)),
            'unknown_false_accepts':false_unknown,'unknown_false_acceptance_rate':ratio(false_unknown,len(unknown)),
            'all_accepted_wrong_fraction':ratio(w+false_unknown,c+w+false_unknown),
            'per_identity':perid,'unit':'Curated image query, not complete passage or field ear-tag event'}
    return result

def cluster_intervals(per_identity,seed=26,draws=2000):
    rng=np.random.default_rng(seed);result={}
    for key,known in [('closed_top1_accuracy',True),('correct_accepted_rate',True),('false_accept_rate',False)]:
        values=np.array([r[key] for r in per_identity if r['is_known']==known],dtype=float)
        if not len(values):result[key]=None;continue
        means=np.array([rng.choice(values,len(values),replace=True).mean() for _ in range(draws)])
        result[key]={'macro_mean':float(values.mean()),'identity_clusters':len(values),'percentile_95_interval':np.quantile(means,[.025,.975]).tolist(),'bootstrap_draws':draws}
    return result
