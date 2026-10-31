from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import hashlib,json,math,csv
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;STUDY=ROOT/'delivery/results/study_v2'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def independent_metrics(rows):
    known=[r for r in rows if r['identity'] in protocol['registered_IDs']];unknown=[r for r in rows if r['identity'] not in protocol['registered_IDs']]
    assert len(known)==len(unknown)==30
    C=sum(r['accepted'] and r['predicted_id']==r['identity'] for r in known)
    W=sum(r['accepted'] and r['predicted_id']!=r['identity'] for r in known)
    U=sum(not r['accepted'] for r in known)
    FAR=sum(r['accepted'] for r in unknown)
    TOP=sum(r['predicted_id']==r['identity'] for r in known)
    assert C+W+U==30
    return dict(known_queries=30,unknown_queries=30,known_correct_accepted_C=C,known_wrong_accepted_W=W,
                known_rejected_U=U,unknown_false_accepts=FAR,known_closed_top1_correct=TOP,
                known_correct_accepted_rate=C/30,known_wrong_accepted_rate=W/30,unknown_false_acceptance_rate=FAR/30,known_closed_top1_accuracy=TOP/30)
protocol=load(ROOT/'protocol/study_v2.json');index=load(STUDY/'index.json');summary=load(STUDY/'summary.json')
assert summary['protocol_sha256']==sha(ROOT/'protocol/study_v2.json')
previous_gallery=load(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/gallery_vectors.json')
previous_events=load(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/worker_messages.json')
previous_by_event={r['event_id']:r for r in previous_events if r['kind']=='result'}
assert len(previous_by_event)==12
tensors=load(STUDY/'tensor_hashes.json');assert len(tensors)==660
tensor_index={(r['condition'],r['query_id']):r for r in tensors if r['group']=='real_event_query'}
normmax=0.;cosmax=0.;idmax=0.;oldcpu_gdelta=0.;oldcpu_qdelta=0.;oldcpuscore=0.;decisions=0;dots_total=0;idscores_total=0
all_rows=[];false_cases=[];real_rows=[];models=[];source_comparisons=[];paired=[]
for c in protocol['conditions']:
    modelroot=STUDY/c['name'];z=np.load(modelroot/'embeddings.npz')
    assert {k:z[k].shape for k in z.files}=={'old_gallery':(30,576),'new_gallery':(30,576),'labelled_query':(60,576),'real_event_query':(12,576)}
    for name in z.files:normmax=max(normmax,float(np.max(np.abs(np.linalg.norm(z[name].astype(float),axis=1)-1))))
    pg=np.asarray(previous_gallery['conditions'][c['name']]['features'])
    gdelta=float(np.max(np.abs(pg-z['old_gallery'])));oldcpu_gdelta=max(oldcpu_gdelta,gdelta);assert gdelta<=1e-5
    for j,row in enumerate(index['real_event_queries']):
        older=next(t for t in previous_by_event[row['query_id']]['conditions'] if t['condition']==c['name'])
        assert older['query_tensor_sha256']==tensor_index[(c['name'],row['query_id'])]['tensor_sha256']
        qdelta=float(np.max(np.abs(np.asarray(older['feature_vector'])-z['real_event_query'][j])))
        oldcpu_qdelta=max(oldcpu_qdelta,qdelta);assert qdelta<=1e-5
    current_pair={}
    for gallery_name,gallery_key in [('old_Aug14','old_gallery'),('new_Aug19','new_gallery')]:
        grows=index['gallery_sets'][gallery_name];features=z[gallery_key].astype(float);labels=sorted({r['identity'] for r in grows})
        assert labels==protocol['registered_IDs']
        for group,qkey,source_rows in [('curated','labelled_query',index['labelled_queries']),('real_event','real_event_query',index['real_event_queries'])]:
            predictions=load(modelroot/(gallery_name+'_'+group+'_predictions.json'));assert len(predictions)==len(source_rows)
            for qi,(row,query) in enumerate(zip(predictions,z[qkey].astype(float))):
                assert row['query_id']==source_rows[qi]['query_id'] and row['threshold']==c['threshold']
                actual=[math.fsum(float(a)*float(b) for a,b in zip(query,reference)) for reference in features];dots_total+=len(actual)
                cosmax=max(cosmax,max(abs(a-b) for a,b in zip(actual,row['gallery_image_cosines'])))
                expected={identity:max(actual[k] for k,r in enumerate(grows) if r['identity']==identity) for identity in labels};idscores_total+=len(labels)
                idmax=max(idmax,max(abs(expected[identity]-row['identity_scores'][identity]) for identity in labels))
                winner=max(labels,key=lambda identity:expected[identity])
                assert winner==row['predicted_id'] and (expected[winner]>=c['threshold'])==row['accepted']
                assert abs(expected[winner]-row['similarity'])<1e-12;decisions+=1
                best_img=max((i for i,r in enumerate(grows) if r['identity']==winner),key=lambda k:actual[k])
                if group=='curated':
                    assert row['is_known']==(row['identity'] in labels)
                    if row['accepted'] and (not row['is_known'] or winner!=row['identity']):
                        false_cases.append({'condition':c['name'],'gallery_condition':gallery_name,'query_id':row['query_id'],
                            'true_anonymous_id':row['identity'],'query_is_registered':row['is_known'],'candidate_id':winner,
                            'cosine':row['similarity'],'threshold':c['threshold'],'query_local_path':source_rows[qi]['local_path'],
                            'gallery_local_path':grows[best_img]['local_path'],'gallery_filename':grows[best_img]['source_filename']})
                else:
                    assert row['identity_reference'] is None and row['verified_identity'] is False and row['eligible_for_identity_accuracy'] is False
                    real_rows.append({'condition':c['name'],'gallery_condition':gallery_name,'query_id':row['query_id'],'source_frame0':row['source_frame0'],
                        'predicted_id':winner,'similarity':row['similarity'],'threshold':c['threshold'],'accepted':row['accepted'],
                        'margin':row['similarity']-c['threshold'],'verified_identity':False})
                    if gallery_name=='old_Aug14':
                        prev=next(t for t in previous_by_event[row['query_id']]['conditions'] if t['condition']==c['name'])
                        assert prev['candidate_anonymous_id']==winner and prev['passes_frozen_threshold']==row['accepted']
                        oldcpuscore=max(oldcpuscore,abs(prev['cosine_similarity']-row['similarity']))
            if group=='curated':
                metric=independent_metrics(predictions);saved=load(modelroot/(gallery_name+'_summary.json'))['curated_metrics']
                assert all(metric[k]==saved[k] for k in metric);current_pair[gallery_name]=predictions
                all_rows.append({'condition':c['name'],'gallery_condition':gallery_name,**metric})
    for identity in sorted({r['identity'] for r in current_pair['old_Aug14']}):
        old=[r for r in current_pair['old_Aug14'] if r['identity']==identity];new=[r for r in current_pair['new_Aug19'] if r['identity']==identity]
        assert len(old)==len(new)==5 and [r['query_id'] for r in old]==[r['query_id'] for r in new]
        known=identity in protocol['registered_IDs']
        paired.append({'condition':c['name'],'anonymous_id':identity,'registered':known,
            'old_C':sum(r['accepted'] and r['predicted_id']==identity for r in old) if known else None,
            'new_C':sum(r['accepted'] and r['predicted_id']==identity for r in new) if known else None,
            'old_W':sum(r['accepted'] and r['predicted_id']!=identity for r in old) if known else None,
            'new_W':sum(r['accepted'] and r['predicted_id']!=identity for r in new) if known else None,
            'old_FAR_count':sum(r['accepted'] for r in old) if not known else None,
            'new_FAR_count':sum(r['accepted'] for r in new) if not known else None})
    models.append({'condition':c['name'],'CPU_oldgallery_component_maxdelta_to_previous_source_worker':gdelta,'threshold':c['threshold'],
                   'new_and_old_gallery_share_exact_same_query_tensor_and_features':True})
assert decisions==720 and dots_total==21600 and idscores_total==4320 and normmax<2e-6 and max(cosmax,idmax)<1e-12
assert oldcpu_qdelta<1e-5 and oldcpuscore<1e-5
assert sum(r['accepted'] for r in real_rows if r['gallery_condition']=='old_Aug14')==3
assert sum(r['accepted'] for r in real_rows if r['gallery_condition']=='new_Aug19')==1
new_false=[r for r in false_cases if r['gallery_condition']=='new_Aug19'];assert len(new_false)==8
save(ROOT/'results/independent_verification.json',{'status':'ALL720_DECISIONS21600_DOTS4320_ID_SCORES_AND_PRIOR60_REAL_CPU_QUERIES_INDEPENDENTLY_VERIFIED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/study_v2.json'),
    'verified_decisions':decisions,'scalar_dot_products':dots_total,'per_identity_max_scores':idscores_total,
    'max_scalar_dot_delta':cosmax,'max_identity_score_delta':idmax,'maximum_feature_unitnorm_error':normmax,
    'prior_CPU_gallery_max_feature_delta':oldcpu_gdelta,'prior_CPU_actual_query_max_feature_delta':oldcpu_qdelta,
    'prior_CPU_actual_query_max_similarity_delta':oldcpuscore,'prior_CPU_real60_tensor_hashes_exact':True,
    'old_GPU_all300_candidates_acceptances_exact':True,'new_gallery_false_accept_case_config_pairs':len(new_false),
    'old_real_candidate_event_model_pairs':3,'new_real_candidate_event_model_pairs':1,'new_real_candidate_events':1,
    'real_query_identity_accuracy_computed':False,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False,
    'metrics':all_rows,'models':models})
save(ROOT/'results/all_false_accept_cases.json',false_cases);save(ROOT/'results/paired_identity_outcomes.json',paired);save(ROOT/'results/all_real_event_outcomes.json',real_rows)
for name,rows in [('metrics',all_rows),('real_event_outcomes',real_rows),('paired_identity_outcomes',paired)]:
    path=ROOT/'results'/(name+'.csv');assert not path.exists()
    with path.open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'decisions':decisions,'scalar_dots':dots_total,'max_dot_delta':cosmax,'prior_cpu_gallery_delta':oldcpu_gdelta,
'prior_cpu_actual_query_delta':oldcpu_qdelta,'prior_cpu_score_delta':oldcpuscore,'new_false_cases':len(new_false),
'new_false_query_IDs':sorted({r['true_anonymous_id'] for r in new_false}),'new_real_candidates':1}))
