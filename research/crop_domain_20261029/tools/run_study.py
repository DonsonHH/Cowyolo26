"""Validation-only crop/threshold selection, then frozen development evaluation."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,hashlib,time,resource
os.environ['CUDA_VISIBLE_DEVICES']='';os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4'
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
import numpy as np
from PIL import Image
import torch,torchvision
from torchvision.models import mobilenet_v3_small,MobileNet_V3_Small_Weights
sys.path.insert(0,str(ROOT/'input'))
from training_primitives import BodyTransform
from identity_metrics import calibrate_threshold,summarise
from crop_rules import apply_rule
torch.set_num_threads(4);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
assert not torch.cuda.is_available()
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    started=time.monotonic_ns();protocol=load(ROOT/'protocol/study_v1.json');audit=load(ROOT/'results/input_audit.json')
    assert audit['protocol_sha256']==sha(ROOT/'protocol/study_v1.json')
    assert audit['status']=='OFFICIAL25_NEW_VALIDATION_GALLERY_AND182_INPUT_IMAGES_DECODED_NO_EXACT_CROSS_ROLE_DUPLICATES'
    for name,digest in protocol['input_metadata_sha256'].items():assert sha(ROOT/'input'/name)==digest
    output=ROOT/'results/study';output.mkdir(exist_ok=False);groups=audit['groups']
    evaluation_enabled=False;cache={};access_log=[];tensor_log=[];image_log=[];forward_batches=[];forwards=0;models={};transforms={};validation=[]
    def image(row,group):
        if group.startswith('evaluation') or group=='real_event_query':assert evaluation_enabled,'Noevaluationimagebeforefreezegate'
        if row['path'] not in cache:
            file=Path(row['path']);assert sha(file)==row['sha256']
            with Image.open(file) as im:im.load();cache[row['path']]=im.convert('RGB')
            access_log.append({'path':row['path'],'query_id':row['query_id'],'group':group,'evaluation_gate_open':evaluation_enabled,'order':len(access_log)})
        return cache[row['path']]
    def extract(c,rule,group):
        nonlocal forwards
        rows=groups[group];tensors=[]
        for row in rows:
            im,crop=apply_rule(image(row,group),rule,group)
            image_log.append({'condition':c['name'],'rule':rule['name'],'group':group,'query_id':row['query_id'],
            'source_sha256':row['sha256'],'transformed_RGB_pixel_sha256':hashlib.sha256(im.tobytes()).hexdigest(),**crop})
            tensor=transforms[c['name']](im).contiguous()
            tensor_log.append({'condition':c['name'],'rule':rule['name'],'group':group,'query_id':row['query_id'],
            'tensor_shape':list(tensor.shape),'tensor_sha256':hashlib.sha256(tensor.numpy().tobytes()).hexdigest()});tensors.append(tensor)
        vectors=[]
        batches=[torch.stack(tensors)] if group.endswith('gallery') else [v.unsqueeze(0) for v in tensors]
        with torch.inference_mode():
            for batch in batches:
                z=torch.nn.functional.normalize(models[c['name']](batch),dim=1).numpy()
                assert np.isfinite(z).all() and z.shape==(len(batch),576);vectors.append(z);forwards+=len(batch)
                forward_batches.append({'condition':c['name'],'rule':rule['name'],'group':group,'batch_images':len(batch),'cumulative_image_forwards':forwards,'evaluation_gate_open':evaluation_enabled})
        return np.concatenate(vectors)
    def retrieve(gallery,query,grows,qrows,c):
        labels=sorted({r['identity'] for r in grows});dots=query.astype(float)@gallery.astype(float).T
        scores=np.stack([dots[:,[i for i,r in enumerate(grows) if r['identity']==identity]].max(1) for identity in labels],axis=1)
        result=[]
        for row,dot,score in zip(qrows,dots,scores):
            j=int(np.argmax(score));r={'query_id':row['query_id'],'predicted_id':labels[j],'similarity':float(score[j]),
                'source_sha256':row['sha256'],'gallery_image_cosines':dot.tolist(),'identity_scores':dict(zip(labels,score.tolist()))}
            if 'identity' in row:r.update({'identity':row['identity'],'is_known':row['identity'] in labels})
            else:r.update({'identity_reference':None,'verified_identity':False,'source_frame0':row['source_frame0']})
            result.append(r)
        return result
    def threshold_rows(rows,threshold):
        return [{**r,'threshold':threshold,'accepted':bool(r['similarity']>=threshold)} for r in rows]
    for c in protocol['conditions']:
        checkpoint=Path(c['checkpoint']);assert sha(checkpoint)==c['checkpoint_sha256']
        base=mobilenet_v3_small(weights=None)
        if c['seed'] is None:base.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
        model=torch.nn.Sequential(base.features,base.avgpool,torch.nn.Flatten()).eval()
        if c['seed'] is not None:model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
        for parameter in model.parameters():parameter.requires_grad_(False)
        models[c['name']]=model;transforms[c['name']]=MobileNet_V3_Small_Weights.IMAGENET1K_V1.transforms() if c['preprocess']=='official' else BodyTransform()
        for ri,rule in enumerate(protocol['crop_rules']):
            destination=output/(c['name']+'__'+rule['name']);destination.mkdir(exist_ok=False)
            gallery=extract(c,rule,'validation_gallery');query=extract(c,rule,'validation_query')
            np.savez_compressed(destination/'validation_embeddings.npz',gallery=gallery,query=query)
            rows=retrieve(gallery,query,groups['validation_gallery'],groups['validation_query'],c)
            calibration=calibrate_threshold([r['similarity'] for r in rows],[r['predicted_id'] for r in rows],[r['identity'] for r in rows],[r['is_known'] for r in rows])
            metrics={}
            for method,t in [('original_fixed',c['threshold']),('validation_calibrated',calibration['threshold'])]:
                predictions=threshold_rows(rows,t);save(destination/('validation_'+method+'_predictions.json'),predictions);metrics[method]=summarise(predictions)
            val={'condition':c['name'],'rule':rule['name'],'selection_eligible':rule['selection_eligible'],'rule_index':ri,'calibration':calibration,'metrics':metrics}
            validation.append(val);save(destination/'validation_summary.json',val)
        print(json.dumps({'validation_encoder_complete':c['name'],'image_forwards':forwards}),flush=True)
    assert forwards==1600 and not evaluation_enabled and len(access_log)==80
    choices=[]
    for c in protocol['conditions']:
        options=[r for r in validation if r['condition']==c['name'] and r['selection_eligible']]
        def key(r):
            m=r['metrics']['validation_calibrated'];return(m['known_correct_accepted_C'],-m['known_wrong_accepted_W'],m['known_closed_top1_correct'],-r['rule_index'])
        selected=max(options,key=key);choices.append({'condition':c['name'],'selected_rule':selected['rule'],'threshold':selected['calibration']['threshold'],
            'validation_C_W_Top1':[selected['metrics']['validation_calibrated'][k] for k in ['known_correct_accepted_C','known_wrong_accepted_W','known_closed_top1_correct']]})
    frozen={'status':'ALL5_RULE_SELECTIONS_AND20_THRESHOLDS_FROZEN_BEFORE_CURRENT_EVALUATION_IMAGE_ACCESS','created_UTC':datetime.now(timezone.utc).isoformat(),
        'protocol_sha256':sha(ROOT/'protocol/study_v1.json'),'choices':choices,'validation_conditions':validation,
        'evaluation_image_accesses':0,'validation_image_accesses':len(access_log),'image_forwards_before_evaluation':forwards,
        'validation_unknown_maximum_false_accepts_allowed':1,'negative_orientation_rule_selectable':False}
    save(output/'selection_frozen.json',frozen);freeze_hash=sha(output/'selection_frozen.json')
    save(output/'accesses_at_freeze.json',access_log)
    evaluation_enabled=True;evaluation=[];regressions=[]
    for c in protocol['conditions']:
        oldroot=PROJECT/'crossdate_gallery_20261029/results/study_v2'/c['name']
        for rule in protocol['crop_rules']:
            assert sha(output/'selection_frozen.json')==freeze_hash
            destination=output/(c['name']+'__'+rule['name'])
            gallery=extract(c,rule,'evaluation_gallery');query=extract(c,rule,'evaluation_query');real=extract(c,rule,'real_event_query')
            np.savez_compressed(destination/'evaluation_embeddings.npz',gallery=gallery,query=query,real_event_query=real)
            labelled=retrieve(gallery,query,groups['evaluation_gallery'],groups['evaluation_query'],c)
            events=retrieve(gallery,real,groups['evaluation_gallery'],groups['real_event_query'],c)
            calibration=next(r for r in validation if r['condition']==c['name'] and r['rule']==rule['name'])['calibration']
            if rule['name']=='P0_original':
                with np.load(oldroot/'embeddings.npz') as prev:
                    gdelta=float(np.max(np.abs(prev['new_gallery']-gallery)));qdelta=float(np.max(np.abs(prev['labelled_query']-query)));rdelta=float(np.max(np.abs(prev['real_event_query']-real)))
                previous=load(oldroot/'new_Aug19_curated_predictions.json');previous_real=load(oldroot/'new_Aug19_real_event_predictions.json')
                labelled_fixed=threshold_rows(labelled,c['threshold']);real_fixed=threshold_rows(events,c['threshold'])
                actual=[*labelled_fixed,*real_fixed];old=[*previous,*previous_real]
                exact=all(a['query_id']==b['query_id'] and a['predicted_id']==b['predicted_id'] and a['accepted']==b['accepted'] for a,b in zip(actual,old))
                score_delta=max(abs(a['similarity']-b['similarity']) for a,b in zip(actual,old))
                regression={'condition':c['name'],'all72_previous_decisions_exact':exact,'gallery_feature_delta':gdelta,'labelled_query_feature_delta':qdelta,'real_query_feature_delta':rdelta,'similarity_maxdelta':score_delta}
                assert max(gdelta,qdelta,rdelta,score_delta)<=1e-5 and exact;regressions.append(regression);save(destination/'baseline_regression.json',regression)
            for method,threshold in [('original_fixed',c['threshold']),('validation_calibrated',calibration['threshold'])]:
                labelled_p=threshold_rows(labelled,threshold);event_p=threshold_rows(events,threshold)
                save(destination/('evaluation_'+method+'_predictions.json'),labelled_p);save(destination/('real_event_'+method+'_predictions.json'),event_p)
                selected=next(r for r in choices if r['condition']==c['name'])
                result={'condition':c['name'],'rule':rule['name'],'threshold_method':method,'threshold':threshold,
                    'is_validation_selected_rule':rule['name']==selected['selected_rule'],'curated_metrics':summarise(labelled_p),
                    'real_event_queries':12,'real_event_passed_threshold':sum(r['accepted'] for r in event_p),
                    'real_event_accepted_candidates':[r for r in event_p if r['accepted']],'real_event_identity_accuracy_admitted':False}
                save(destination/('evaluation_'+method+'_summary.json'),result);evaluation.append(result)
        print(json.dumps({'evaluation_encoder_complete':c['name'],'image_forwards':forwards}),flush=True)
    assert forwards==3640 and len(tensor_log)==len(image_log)==3640 and len(access_log)==182
    assert all(r['evaluation_gate_open'] for r in access_log[80:]) and not any(r['evaluation_gate_open'] for r in access_log[:80])
    save(output/'tensor_log.json',tensor_log);save(output/'image_transform_log.json',image_log);save(output/'access_log.json',access_log);save(output/'forward_batches.json',forward_batches)
    save(output/'input_index.json',groups)
    result={'status':'FROZEN_VALIDATION_CROP_AND_THRESHOLD_CHOICES_WITH_ALL40_EVALUATION_CONDITIONS_COMPLETE',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_JOB_ID':os.environ['SLURM_JOB_ID'],'device':'CPU','torch_version':torch.__version__,'torchvision_version':torchvision.__version__,
        'protocol_sha256':sha(ROOT/'protocol/study_v1.json'),'frozen_selection_sha256':freeze_hash,'input_audit_sha256':sha(ROOT/'results/input_audit.json'),
        'validation_model_rule_conditions':20,'evaluation_model_rule_threshold_conditions':40,'validation_decisions':2200,'evaluation_curated_decisions':2400,'real_event_decisions':480,
        'actual_image_forwards':forwards,'validation_image_forwards':1600,'evaluation_image_forwards':2040,'unique_source_images':182,
        'all_rule_selected_choices':choices,'baseline_regressions':regressions,'evaluation_conditions':evaluation,
        'no_rule_selected_on_evaluation_outputs':True,'P3_orientation_control_not_selectable':True,'new_training_updates':0,
        'new_independent_test':False,'real_event_identity_accuracy_admitted':False,'real_RF_hardware_connected':False,'FPGA_execution_verified':False,'whole_goal_complete':False,
        'wall_time_s':(time.monotonic_ns()-started)/1e9,'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    save(output/'summary.json',result)
    manifest=[{'relative_file':file.relative_to(ROOT).as_posix(),'bytes':file.stat().st_size,'sha256':sha(file)} for file in sorted(output.rglob('*')) if file.is_file()]
    save(ROOT/'results/artifact_manifest.json',manifest)
    print(json.dumps({k:v for k,v in result.items() if k not in ['evaluation_conditions','baseline_regressions']}),flush=True)
if __name__=='__main__':main()
