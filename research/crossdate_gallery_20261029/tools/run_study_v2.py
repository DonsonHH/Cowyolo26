"""Actual CPU encoder forwards, frozen thresholds; gallery intervention only."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,hashlib,json,time,resource
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
import numpy as np
from PIL import Image
import torch,torchvision
from torchvision.models import mobilenet_v3_small,MobileNet_V3_Small_Weights
sys.path.insert(0,str(ROOT/'input'))
from training_primitives import BodyTransform
from identity_metrics import summarise
torch.set_num_threads(4);torch.set_num_interop_threads(1)
assert not torch.cuda.is_available();torch.use_deterministic_algorithms(True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    start=time.monotonic_ns();protocol=load(ROOT/'protocol/study_v2.json');audit=load(ROOT/'results/input_audit.json')
    assert sha(ROOT/'protocol/study_v1.json')==audit['protocol_sha256']
    assert sha(ROOT/'protocol/study_v1.json')==protocol['original_protocol_sha256']
    assert audit['status']=='NEW30_AUG19_GALLERY_RELEASE_HASHES_FULL_DECODE_AND132_INPUT_CROSS_ROLE_DUPLICATES_VERIFIED'
    for name,digest in protocol['input_module_sha256'].items():assert sha(ROOT/'input'/name)==digest
    gallery_sets={'old_Aug14':load(ROOT/'input/old_gallery.json'),'new_Aug19':audit['new_images']}
    queries=load(ROOT/'input/labelled_queries.json');real=load(ROOT/'input/real_event_queries.json')
    all_rows=[*gallery_sets['old_Aug14'],*gallery_sets['new_Aug19'],*queries,*real]
    for row in all_rows:
        p=Path(row['path']);assert sha(p)==row['sha256'];assert p.is_file()
    out=ROOT/'results/study_v2';out.mkdir(exist_ok=False);images={}
    for row in all_rows:
        with Image.open(row['path']) as im:im.load();images[row['path']]=im.convert('RGB')
    for row in queries:row['query_id']=row['relative_path']
    summary=[];actual_image_forwards=0;tensor_rows=[];regressions=[]
    def extract(encoder,transform,rows,condition,group):
        nonlocal actual_image_forwards
        tensors=[transform(images[r['path']]).contiguous() for r in rows]
        for row,tensor in zip(rows,tensors):tensor_rows.append({'condition':condition,'group':group,'path':row['path'],'query_id':row.get('query_id'),
            'tensor_shape':list(tensor.shape),'tensor_sha256':hashlib.sha256(tensor.numpy().tobytes()).hexdigest()})
        features=[]
        with torch.inference_mode():
            batches=[torch.stack(tensors)] if group.endswith('gallery') else [x.unsqueeze(0) for x in tensors]
            for batch in batches:features.append(torch.nn.functional.normalize(encoder(batch),dim=1).numpy());actual_image_forwards+=len(batch)
        z=np.concatenate(features);assert z.shape==(len(rows),576) and np.isfinite(z).all();return z
    def retrieve(gallery,grows,features,qrows,c):
        labels=protocol['registered_IDs'];dots=features.astype(np.float64)@gallery.astype(np.float64).T
        scores=np.array([[max(float(v[i]) for i,r in enumerate(grows) if r['identity']==identity) for identity in labels] for v in dots])
        result=[]
        for row,dot,score in zip(qrows,dots,scores):
            best=int(np.argmax(score));entry={'query_id':row['query_id'],'input_path':row['path'],'predicted_id':labels[best],
                'similarity':float(score[best]),'accepted':bool(score[best]>=c['threshold']),'threshold':c['threshold'],
                'source_image_sha256':row['sha256'],'gallery_image_cosines':dot.tolist(),'identity_scores':dict(zip(labels,score.tolist()))}
            if 'identity' in row:entry.update({k:row[k] for k in ['identity','role','relative_path','day']});entry['is_known']=row['identity'] in labels
            else:entry.update({'source_frame0':row['source_frame0'],'event_source_frame0':row['event_source_frame0'],
                              'identity_reference':None,'verified_identity':False,'eligible_for_identity_accuracy':False})
            result.append(entry)
        return result
    for c in protocol['conditions']:
        checkpoint=Path(c['checkpoint']);assert sha(checkpoint)==c['checkpoint_sha256']
        base=mobilenet_v3_small(weights=None)
        if c['seed'] is None:base.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
        encoder=torch.nn.Sequential(base.features,base.avgpool,torch.nn.Flatten()).eval()
        if c['seed'] is not None:encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
        for p in encoder.parameters():p.requires_grad_(False)
        transform=MobileNet_V3_Small_Weights.IMAGENET1K_V1.transforms() if c['preprocess']=='official' else BodyTransform()
        destination=out/c['name'];destination.mkdir(exist_ok=False);model_start=time.monotonic_ns()
        old_z=extract(encoder,transform,gallery_sets['old_Aug14'],c['name'],'old_Aug14_gallery')
        curated_z=extract(encoder,transform,queries,c['name'],'labelled_curated_query')
        baseline=next(b for b in protocol['baselines'] if b['condition']==c['name'])
        assert sha(Path(baseline['prediction_path']))==baseline['prediction_sha256'];assert sha(Path(baseline['feature_path']))==baseline['feature_sha256']
        with np.load(baseline['feature_path']) as previous:
            gdiff=float(np.max(np.abs(previous['gallery']-old_z)));qdiff=float(np.max(np.abs(previous['query']-curated_z)))
        old_predictions=retrieve(old_z,gallery_sets['old_Aug14'],curated_z,queries,c);old_saved=load(Path(baseline['prediction_path']))
        assert len(old_saved)==60
        maximum_score_diff=max(abs(a['similarity']-b['similarity']) for a,b in zip(old_predictions,old_saved))
        counts={k:summarise(old_predictions)[k] for k in ['known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts','known_closed_top1_correct']}
        decision_exact=all(a['relative_path']==b['relative_path'] and a['identity']==b['identity'] and a['predicted_id']==b['predicted_id'] and a['accepted']==b['accepted'] for a,b in zip(old_predictions,old_saved))
        regression={'condition':c['name'],'old_gallery_maximum_feature_abs_delta':gdiff,'old_curated_query_maximum_feature_abs_delta':qdiff,
                    'old_similarity_maximum_abs_delta':maximum_score_diff,'old_all60_candidate_and_acceptance_exact':decision_exact,'old_metrics':counts}
        regressions.append(regression)
        tol=protocol['old_baseline_tolerances']
        cpu_reference=protocol['previous_CPU_gallery_reference'];assert sha(Path(cpu_reference['path']))==cpu_reference['sha256']
        cpu_saved=load(Path(cpu_reference['path']));assert len(cpu_saved['entries'])==30
        assert [r['relative_path'] for r in cpu_saved['entries']]==[r['relative_path'] for r in gallery_sets['old_Aug14']]
        cpu_z=np.asarray(cpu_saved['conditions'][c['name']]['features'],dtype=np.float32)
        cpu_delta=float(np.max(np.abs(cpu_z-old_z)));regression['old_CPU_gallery_maximum_feature_abs_delta']=cpu_delta
        regression['GPU_component_threshold_exceeded_diagnostic']=max(gdiff,qdiff)>tol['maximum_feature_absolute_difference']
        assert cpu_delta<=tol['maximum_feature_absolute_difference'] and maximum_score_diff<=tol['maximum_similarity_absolute_difference']
        assert decision_exact and all(counts[k]==baseline['expected_summary'][k] for k in counts)
        save(destination/'old_baseline_regression.json',regression)
        new_z=extract(encoder,transform,gallery_sets['new_Aug19'],c['name'],'new_Aug19_gallery')
        real_z=extract(encoder,transform,real,c['name'],'real_event_query')
        np.savez_compressed(destination/'embeddings.npz',old_gallery=old_z,new_gallery=new_z,labelled_query=curated_z,real_event_query=real_z)
        for gallery_name,z in [('old_Aug14',old_z),('new_Aug19',new_z)]:
            known=retrieve(z,gallery_sets[gallery_name],curated_z,queries,c);events=retrieve(z,gallery_sets[gallery_name],real_z,real,c)
            result={'condition':c['name'],'gallery_condition':gallery_name,'threshold':c['threshold'],
                'curated_metrics':summarise(known),'real_event_queries':12,'real_event_passed_fixed_threshold':sum(r['accepted'] for r in events),
                'real_event_verified_identity_count':0,'real_event_accuracy_computed':False,'real_accepted_candidates':[r for r in events if r['accepted']],
                'source_gallery_samepassage_pair_excluded_from_independent_evaluation':gallery_name=='old_Aug14',
                'retrospective_only_for_Aug14source':gallery_name=='new_Aug19'}
            save(destination/(gallery_name+'_curated_predictions.json'),known);save(destination/(gallery_name+'_real_event_predictions.json'),events)
            save(destination/(gallery_name+'_summary.json'),result);summary.append(result)
        print(json.dumps({'finished_model':c['name'],'actual_image_forwards_so_far':actual_image_forwards,'elapsed_model_s':(time.monotonic_ns()-model_start)/1e9}),flush=True)
        del encoder,base
    assert actual_image_forwards==5*(30+30+60+12)==660
    save(out/'tensor_hashes.json',tensor_rows);save(out/'index.json',{'gallery_sets':gallery_sets,'labelled_queries':queries,'real_event_queries':real})
    result={'status':'FIVE_FROZEN_CPU_ENCODERS_TWO_DATE_GALLERIES_ON60_LABELLED_AND12_REAL_EVENT_QUERIES_COMPLETE',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/study_v2.json'),'input_audit_sha256':sha(ROOT/'results/input_audit.json'),
        'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'device':'CPU','torch_version':torch.__version__,'torchvision_version':torchvision.__version__,
        'actual_image_forwards':actual_image_forwards,'query_image_forwards':5*(60+12),'gallery_image_forwards':5*60,
        'retrieval_decisions':5*2*(60+12),'model_gallery_conditions':10,'conditions':summary,'old_baseline_regressions':regressions,
        'new_training_updates':0,'threshold_changes':0,'all_event_identity_references_unavailable':True,'ear_tag_registry_mapping_proven':False,
        'new_independent_test':False,'FPGA_execution_verified':False,'whole_goal_complete':False,
        'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'study_wall_s':(time.monotonic_ns()-start)/1e9}
    save(out/'summary.json',result)
    manifest=[]
    for file in sorted(out.rglob('*')):
        if file.is_file():manifest.append({'relative_file':file.relative_to(ROOT).as_posix(),'bytes':file.stat().st_size,'sha256':sha(file)})
    save(ROOT/'results/artifact_manifest.json',manifest)
    print(json.dumps({k:v for k,v in result.items() if k not in ['conditions','old_baseline_regressions']}),flush=True)
if __name__=='__main__':main()
