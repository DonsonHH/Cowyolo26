"""Second-platform graph execution and independent saved-feature scoring.

Local ONNX/ORT dependencies are task-local. No Torch or original scorer is used.
FP32 parity and QDQ portability findings are reported separately.
"""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,platform,sys,tarfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'local_dependencies'))
import numpy as np
import onnx,onnxruntime as ort
from onnx import numpy_helper
from PIL import Image,ImageOps

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def session(path):
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
def preprocess(row):
    path=ROOT.parent/'identity_training_20261026/delivery'/row['relative_path']
    with Image.open(path) as image:image=ImageOps.pad(image.convert('RGB'),(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127),centering=(.5,.5))
    value=np.asarray(image).transpose(2,0,1).astype(np.float32)/np.float32(255.)
    value=(value-np.array([.485,.456,.406],dtype=np.float32)[:,None,None])/np.array([.229,.224,.225],dtype=np.float32)[:,None,None]
    return np.ascontiguousarray(value[None])
def graph_counts(path):
    model=onnx.load(path);onnx.checker.check_model(model,full_check=True)
    inference=onnx.shape_inference.infer_shapes(model,strict_mode=True,data_prop=True)
    shapes={v.name:[int(d.dim_value) if d.HasField('dim_value') else None for d in v.type.tensor_type.shape.dim] for v in list(inference.graph.value_info)+list(inference.graph.input)+list(inference.graph.output)}
    initializers={v.name:numpy_helper.to_array(v) for v in model.graph.initializer};producers={out:node for node in model.graph.node for out in node.output}
    macs=matmul=0;groups=Counter()
    for node in model.graph.node:
        shape=shapes.get(node.output[0],[])
        if not shape or any(d is None for d in shape):continue
        if node.op_type=='MatMul':
            a=shapes.get(node.input[0]);b=shapes.get(node.input[1])
            if a and b and len(a)>=2 and all(d is not None for d in a+b):matmul+=int(np.prod(shape))*a[-1]
        if node.op_type!='Conv':continue
        weight=node.input[1]
        if weight not in initializers and weight in producers and producers[weight].op_type=='DequantizeLinear':weight=producers[weight].input[0]
        array=initializers.get(weight)
        if array is None:continue
        macs+=int(np.prod(shape))*int(np.prod(array.shape[1:]))
        groups[next((int(a.i) for a in node.attribute if a.name=='group'),1)]+=1
    return {'node_counts':dict(Counter(n.op_type for n in model.graph.node)),
            'initializer_bytes':sum(a.nbytes for a in initializers.values()),
            'initializer_dtype_bytes':dict(Counter({dtype:sum(a.nbytes for a in initializers.values() if str(a.dtype)==dtype) for dtype in {str(a.dtype) for a in initializers.values()}})),
            'Conv_MACs_including_QDQ_weight_shapes':macs,'MatMul_MACs_known_shapes':matmul,'Conv_groups_histogram':dict(groups)}
def predict(g,q,gs,qs):
    labels=sorted({r['identity'] for r in gs});scores=np.stack([(q.astype(float)@g[[i for i,r in enumerate(gs) if r['identity']==label]].astype(float).T).max(1) for label in labels],axis=1)
    return [{'identity':r['identity'],'known':r['identity'] in labels,'prediction':labels[int(np.argmax(values))],
             'score':float(values.max()),'relative_path':r['relative_path']} for r,values in zip(qs,scores)]
def calibrate(rows):
    groups=defaultdict(list)
    for r in rows:groups[r['score']].append(r)
    count_unknown=sum(not r['known'] for r in rows);assert count_unknown>0
    best=(0,0,float(np.nextafter(max(groups),np.inf)));correct=wrong=unknown=0
    for score,group in sorted(groups.items(),reverse=True):
        for r in group:
            if not r['known']:unknown+=1
            elif r['identity']==r['prediction']:correct+=1
            else:wrong+=1
        candidate=correct,-wrong,score
        if unknown/count_unknown<=.05+1e-12 and candidate>best:best=candidate
    return best[2]
def counts(rows,tau):
    c=Counter()
    for r in rows:
        accept=r['score']>=tau
        if r['known']:
            c['known_queries']+=1;c['known_closed_top1_correct']+=r['identity']==r['prediction']
            c['known_rejected_U' if not accept else 'known_correct_accepted_C' if r['prediction']==r['identity'] else 'known_wrong_accepted_W']+=1
        else:c['unknown_queries']+=1;c['unknown_false_accepts']+=accept
    return {k:int(c[k]) for k in ['known_queries','unknown_queries','known_closed_top1_correct','known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']}

def main():
    record=json.loads((ROOT/'results/bundle_record.json').read_text());bundle=ROOT/'results/export_delivery.tar.gz'
    assert bundle.stat().st_size==record['bytes'] and sha(bundle)==record['sha256']
    dest=ROOT/'delivery'
    if not dest.exists():
        dest.mkdir()
        with tarfile.open(bundle) as archive:archive.extractall(dest,filter='data')
    manifest=json.loads((dest/'delivery_manifest.json').read_text())
    for row in manifest:
        path=(dest/row['path']).resolve();assert path.is_relative_to(dest.resolve())
        assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256']
    for relative in ['tools/export_and_quantise.py','tools/graph_audit.py','tools/bounded_quantisation.py','protocol/export_ptq_v1.json']:
        assert sha(ROOT/relative)==sha(dest/relative),relative
    out=dest/'results/export_audit';summary=json.loads((out/'summary.json').read_text());p=json.loads((dest/'protocol/export_ptq_v1.json').read_text())
    assert summary['protocol_sha256']==sha(dest/'protocol/export_ptq_v1.json')
    assert sha(out/'all_quantised_thresholds_frozen.json')==summary['quantised_threshold_freeze_sha256']
    index=json.loads((out/'feature_index.json').read_text());calibration=json.loads((out/'ptq_calibration_training_only.json').read_text())
    assert len(calibration)==64 and all(r['split']=='train' for r in calibration)
    assert not {r['identity'] for r in calibration}&{r['identity'] for rows in index.values() for r in rows}
    graph_results={};det_path=out/'detector/yolo26n_pilot.onnx';detgraph=graph_counts(det_path)
    assert detgraph['initializer_bytes']==summary['detector_graph']['initializer_bytes']
    assert detgraph['Conv_MACs_including_QDQ_weight_shapes']==summary['detector_graph']['Conv_MACs_direct_initializer_only']
    graph_results['detector']=detgraph;vectors=np.load(out/'detector/parity_vectors.npz');runtime=session(det_path);det_checks=[]
    for image,reference in zip(vectors['inputs'],vectors['torch_outputs']):
        output=runtime.run(None,{'images':image[None]})[0][0];a=reference[reference[:,4]>=.2];b=output[output[:,4]>=.2]
        assert len(a)==len(b);available=set(range(len(b)));err=score_error=0.
        for row in a:
            j=min(available,key=lambda i:float(np.abs(row[:4]-b[i,:4]).sum())+1000*(row[5]!=b[i,5]));available.remove(j)
            assert row[5]==b[j,5];err=max(err,float(np.abs(row[:4]-b[j,:4]).max()));score_error=max(score_error,float(abs(row[4]-b[j,4])))
        assert err<.02 and score_error<1e-4
        det_checks.append({'detections':len(a),'max_coordinate_error_input_pixels':err,'max_score_error':score_error,'torch_vs_local_ORT_strong_detection_parity':'PASS'})
    del runtime
    conditions=[];local_forward=[]
    for condition in summary['identity_conditions']:
        name=condition['name'];folder=out/name
        assert sha(folder/'embedding_fp32.onnx')==condition['fp32_sha256'] and sha(folder/'embedding_conv_qdq.onnx')==condition['qdq_sha256']
        validation=np.load(folder/'validation_embeddings.npz');evaluation=np.load(folder/'evaluation_embeddings.npz')
        for precision,file,audit_name in [('fp32','embedding_fp32.onnx','fp32_graph'),('qdq','embedding_conv_qdq.onnx','qdq_graph')]:
            graph=graph_counts(folder/file);reference=condition[audit_name]
            assert graph['node_counts']==reference['operator_counts'] and graph['initializer_bytes']==reference['initializer_bytes']
            assert graph['Conv_MACs_including_QDQ_weight_shapes']==condition['fp32_graph']['Conv_MACs_direct_initializer_only']
            graph_results[name+'_'+precision]=graph
            if precision=='qdq':
                rows=predict(validation['qdq_gallery'],validation['qdq_query'],index['validation_gallery'],index['validation_query'])
                threshold=calibrate(rows);assert abs(threshold-condition['qdq_threshold']['threshold'])<1e-12
            else:threshold=condition['original_fp32_threshold']
            rows=predict(evaluation[precision+'_gallery'],evaluation[precision+'_query'],index['evaluation_gallery'],index['evaluation_query'])
            recalculated=counts(rows,threshold);assert all(v==condition[precision+'_evaluation'][k] for k,v in recalculated.items())
            runtime=session(folder/file)
            for split,key,subset in [('validation_gallery','gallery',validation),('validation_query','query',validation),('evaluation_gallery','gallery',evaluation),('evaluation_query','query',evaluation)]:
                for i in range(min(2,len(index[split]))):
                    row=index[split][i];vector=runtime.run(None,{'images':preprocess(row)})[0][0]
                    old=subset[precision+'_'+key][i];error=float(np.abs(vector-old).max())
                    passed=bool(np.allclose(vector,old,rtol=1e-4,atol=1e-5 if precision=='fp32' else 1e-4))
                    if precision=='fp32':assert passed,(name,split,error)
                    local_forward.append({'condition':name,'precision':precision,'split':split,'source':row['relative_path'],
                        'maximum_feature_error_linux_vs_windows':error,'declared_tolerance_passed':passed})
            conditions.append({'condition':name,'precision':precision,'threshold':threshold,'counts':recalculated,'independent_score_and_threshold_check':'PASS'})
            del runtime
        print(json.dumps({'condition_verified':name}),flush=True)
    qdq_deviations=[r for r in local_forward if r['precision']=='qdq' and not r['declared_tolerance_passed']]
    result={'status':'PASS' if not qdq_deviations else 'FP32_PASS_QDQ_PORTABILITY_DIFFERENCES_RETAINED',
            'bundle_sha256':record['sha256'],'manifest_files_verified':len(manifest),
            'local_runtime':{'python':sys.version,'platform':platform.platform(),'onnx':onnx.__version__,'onnxruntime':ort.__version__,'threads':2},
            'graphs_independently_checked':graph_results,'detector_actual_local_forwards':det_checks,'identity_metrics':conditions,
            'identity_local_forward_checks':local_forward,'QDQ_portability_tolerance_failures':qdq_deviations,
            'calibration_training_only':True,'calibration_images':64,'pynq_or_FPGA_compile_verified':False,
            'scope':'Host Linux export vs Windows CPU numerical replay and independent resource/metric arithmetic. No ARM execution, synthesis, resource place/route, board latency or fresh accuracy benchmark.'}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['graphs_independently_checked','identity_local_forward_checks','QDQ_portability_tolerance_failures']},indent=2))
if __name__=='__main__':main()
