"""Independent training-drift, selection, pixel, graph and holdout arithmetic."""
from pathlib import Path
from collections import defaultdict,Counter
import hashlib,json,sys,tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'deployment_audit_20261026/local_dependencies'))
import numpy as np
import onnx,onnxruntime as ort
from onnx import numpy_helper
from PIL import Image,ImageOps

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def score(g,q,gs,qs):
    ids=sorted({r['identity'] for r in gs})
    matrix=np.stack([(q.astype(float)@g[[i for i,r in enumerate(gs) if r['identity']==identity]].astype(float).T).max(1) for identity in ids],axis=1)
    return [{'relative_path':r['relative_path'],'identity':r['identity'],'known':r['identity'] in ids,'prediction':ids[int(np.argmax(v))],'score':float(v.max())} for r,v in zip(qs,matrix)]
def threshold(rows):
    groups=defaultdict(list)
    for r in rows:groups[r['score']].append(r)
    total=sum(not r['known'] for r in rows);assert total
    best=(0,0,float(np.nextafter(max(groups),np.inf)));c=w=u=0
    for s,group in sorted(groups.items(),reverse=True):
        for r in group:
            if not r['known']:u+=1
            elif r['identity']==r['prediction']:c+=1
            else:w+=1
        candidate=c,-w,s
        if u/total<=.05+1e-12 and candidate>best:best=candidate
    return best[2]
def counts(rows,tau):
    c=Counter()
    for r in rows:
        accepted=r['score']>=tau
        if r['known']:
            c['known_queries']+=1;c['known_closed_top1_correct']+=r['identity']==r['prediction']
            c['known_rejected_U' if not accepted else 'known_correct_accepted_C' if r['identity']==r['prediction'] else 'known_wrong_accepted_W']+=1
        else:c['unknown_queries']+=1;c['unknown_false_accepts']+=accepted
    return {k:int(c[k]) for k in ['known_queries','unknown_queries','known_closed_top1_correct','known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']}
def preprocess(path):
    with Image.open(path) as im:im=ImageOps.pad(im.convert('RGB'),(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127),centering=(.5,.5))
    x=np.asarray(im).transpose(2,0,1).astype(np.float32)/np.float32(255)
    x=(x-np.array([.485,.456,.406],np.float32)[:,None,None])/np.array([.229,.224,.225],np.float32)[:,None,None]
    return np.ascontiguousarray(x[None])
def main():
    record=json.loads((ROOT/'results/bundle_record.json').read_text());bundle=ROOT/'results/quant_diagnosis_delivery.tar.gz'
    assert bundle.stat().st_size==record['bytes'] and sha(bundle)==record['sha256']
    dest=ROOT/'delivery'
    if not dest.exists():
        dest.mkdir()
        with tarfile.open(bundle) as archive:archive.extractall(dest,filter='data')
    manifest=json.loads((dest/'delivery_manifest.json').read_text())
    for row in manifest:
        path=(dest/row['path']).resolve();assert path.is_relative_to(dest.resolve())
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
    for relative in ['tools/probe_activations.py','tools/compare_mixed_precision.py','tools/evaluate_frozen_holdout.py','protocol/mixed_precision_v1.json']:
        assert sha(ROOT/relative)==sha(dest/relative)
    activation=json.loads((dest/'results/activations/summary.json').read_text());witness_checks=[]
    for condition in activation['conditions']:
        assert len(condition['layers'])==52
        derived=next(r for r in condition['layers'] if np.median([x['relative_RMSE'] for x in r['sample_metrics']])>=.2)
        assert derived['node']==condition['first_conv_median_relative_RMSE_ge02']['node']
        data=np.load(dest/'results/activations'/condition['condition']/'first_large_drift_witness.npz')
        a=data['fp32'].astype(float).ravel();b=data['qdq'].astype(float).ravel();relative=float(np.linalg.norm(a-b)/np.linalg.norm(a))
        assert abs(relative-derived['sample_metrics'][0]['relative_RMSE'])<1e-10
        witness_checks.append({'seed':condition['seed'],'first_large_drift_Conv':derived['conv_index'],'witness_RMSE':relative})
    mixed=json.loads((dest/'results/mixed/summary.json').read_text());old_index=json.loads((ROOT.parent/'deployment_audit_20261026/delivery/results/export_audit/feature_index.json').read_text())
    validations=[]
    for condition in mixed['conditions']:
        folder=dest/'results/mixed'/condition['candidate']/condition['source_condition'];features=np.load(folder/'validation_embeddings.npz')
        predictions=score(features['gallery'],features['query'],old_index['validation_gallery'],old_index['validation_query'])
        tau=threshold(predictions);assert abs(tau-condition['validation_threshold']['threshold'])<1e-12
        metrics=counts(predictions,tau);assert all(condition['validation'][k]==v for k,v in metrics.items())
        if condition['candidate']!='full_conv_qdq':
            model=onnx.load(folder/'embedding_mixed_qdq.onnx');onnx.checker.check_model(model,full_check=True)
            initializers={t.name:t for t in model.graph.initializer};producers={o:n for n in model.graph.node for o in n.output}
            for node in model.graph.node:
                if node.op_type!='Conv':continue
                if node.name in condition['excluded_nodes']:assert node.input[1] in initializers and initializers[node.input[1]].data_type==onnx.TensorProto.FLOAT
                else:
                    dq=producers[node.input[1]];assert dq.op_type=='DequantizeLinear' and initializers[dq.input[0]].data_type==onnx.TensorProto.INT8
        validations.append({'candidate':condition['candidate'],'seed':condition['seed'],'counts':metrics})
    protocol=json.loads((dest/'protocol/mixed_precision_v1.json').read_text());rank=[]
    for ordinal,candidate in enumerate(protocol['candidates']):
        group=[r for r in validations if r['candidate']==candidate['name']]
        macs=next(r['excluded_fp32_Conv_MACs'] for r in mixed['conditions'] if r['candidate']==candidate['name'])
        key=[min(r['counts']['known_correct_accepted_C'] for r in group),sum(r['counts']['known_correct_accepted_C'] for r in group)/3,-sum(r['counts']['known_wrong_accepted_W'] for r in group),-macs,-ordinal]
        rank.append({'candidate':candidate['name'],'key':key})
    selected=max(rank,key=lambda r:r['key'])['candidate'];assert selected==mixed['frozen_candidate']['selected_recipe']
    frozen=json.loads((dest/'protocol/future_comparison_frozen.json').read_text());assert selected==frozen['selected_recipe']
    future=dest/'results/future_holdout';summary=json.loads((future/'summary.json').read_text());index=json.loads((future/'feature_index.json').read_text())
    assert sha(dest/'protocol/future_comparison_frozen.json')==summary['protocol_sha256']
    prior=json.loads((ROOT.parent/'identity_training_20261026/delivery/results/input_audit/manifest.json').read_text())+json.loads((ROOT.parent/'identity_baseline_20261026/delivery/results/image_audit/audited_manifest.json').read_text())
    priorids={r['identity'] for r in prior};priorpixels={r['pixel_sha256'] for r in prior};pixels=defaultdict(set)
    image_rows=json.loads((future/'audited_manifest.json').read_text())
    for row in image_rows:
        assert row['identity'] not in priorids and sha(dest/row['relative_path'])==row['sha256']
        with Image.open(dest/row['relative_path']) as image:image.load();image=image.convert('RGB');w,h=image.size;key=hashlib.sha256(w.to_bytes(4,'big')+h.to_bytes(4,'big')+image.tobytes()).hexdigest()
        assert key==row['pixel_sha256'] and key not in priorpixels;pixels[key].add(row['split'])
    assert len(image_rows)==90 and all(len(split)==1 for split in pixels.values())
    future_checks=[];local_checks=[]
    for condition in summary['conditions']:
        file=future/condition['name'];vectors=np.load(file/'embeddings.npz');predictions=score(vectors['gallery'],vectors['query'],index['gallery'],index['query'])
        metrics=counts(predictions,condition['threshold']);assert all(v==condition['metrics'][k] for k,v in metrics.items())
        saved=next(r for r in frozen['conditions'] if r['name']==condition['name'])
        assert saved['threshold']==condition['threshold'] and saved['model_sha256']==condition['model_sha256']
        if condition['method']==selected:
            path=dest/'results/mixed'/selected/f'C_letterbox_trained_seed{condition["seed"]}'/'embedding_mixed_qdq.onnx'
            assert sha(path)==condition['model_sha256'];opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
            runtime=ort.InferenceSession(str(path),sess_options=opts,providers=['CPUExecutionProvider'])
            for split in ['gallery','query']:
                for i in range(2):
                    vector=runtime.run(None,{'images':preprocess(dest/index[split][i]['relative_path'])})[0][0]
                    err=float(np.abs(vector-vectors[split][i]).max());passed=bool(np.allclose(vector,vectors[split][i],rtol=1e-4,atol=1e-5))
                    local_checks.append({'seed':condition['seed'],'split':split,'image':index[split][i]['relative_path'],'max_local_CPU_feature_error':err,
                                         'predeclared_tolerance_passed':passed})
        future_checks.append({'name':condition['name'],'method':condition['method'],'seed':condition['seed'],'counts':metrics})
    portability_failures=[r for r in local_checks if not r['predeclared_tolerance_passed']]
    result={'status':'PASS' if not portability_failures else 'ARITHMETIC_PASS_MIXED_GRAPH_PORTABILITY_DIFFERENCES','bundle_sha256':record['sha256'],'manifest_files':len(manifest),'training_drift_witness_checks':witness_checks,
            'validation_conditions_recalculated':len(validations),'validation_candidate_selection_reproduced':selected,
            'model_Conv_precision_coverage_checked':True,'future_images_decoded':90,'future_IDs_outside_all_previous_cohorts':True,
            'future_identity_counts':{'registered':6,'unknown':6},'fresh_holdout_conditions_recalculated':future_checks,
            'Windows_actual_mixed_graph_forwards':local_checks,'mixed_graph_portability_tolerance_failures':portability_failures,'whole_goal_complete':False,
            'scope':'Independent stored-metric/selection, graph precision, untouched-ID image integrity and selected-model CPU replay; no board or field RFID performance'}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['Windows_actual_mixed_graph_forwards','fresh_holdout_conditions_recalculated']},indent=2))
if __name__=='__main__':main()
