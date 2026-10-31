from pathlib import Path
from collections import Counter
import hashlib,json,os,sys
import numpy as np
import onnx,onnxruntime as ort
from onnx import numpy_helper
from PIL import Image
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'quant_diagnosis';SOURCE=PROJECT/'deployment_audit/results/export_audit'
sys.path.insert(0,str(PROJECT/'identity_training/tools'))
from training_primitives import BodyTransform

def runtime(path,optimised=False,save_optimised_path=None):
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL if optimised else ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    if save_optimised_path is not None:options.optimized_model_filepath=str(save_optimised_path)
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
def geometry(a,b):
    a=a.astype(np.float64).ravel();b=b.astype(np.float64).ravel()
    na=np.linalg.norm(a);nb=np.linalg.norm(b)
    return {'relative_RMSE':float(np.linalg.norm(a-b)/max(na,1e-12)),
            'cosine':float(a@b/max(na*nb,1e-12)),'max_absolute_error':float(np.abs(a-b).max())}
def augment(path,out):
    model=onnx.load(path);model=onnx.shape_inference.infer_shapes(model,strict_mode=True)
    info={v.name:v for v in list(model.graph.value_info)+list(model.graph.output)+list(model.graph.input)}
    convs=[node for node in model.graph.node if node.op_type=='Conv']
    names={v.name for v in model.graph.output}
    for node in convs:
        for name in node.output:
            if name not in names:model.graph.output.append(info[name]);names.add(name)
    onnx.save(model,out);return model,convs
def main():
    OUT=ROOT/'results/activations';OUT.mkdir(parents=True,exist_ok=False)
    samples=json.loads((SOURCE/'ptq_calibration_training_only.json').read_text())[:8]
    assert all(r['split']=='train' for r in samples)
    transform=BodyTransform();inputs=[]
    for r in samples:
        path=PROJECT/'identity_training'/r['relative_path'];assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256']
        with Image.open(path) as im:inputs.append(transform(im.convert('RGB')).numpy()[None])
    summary=[]
    for seed in [26,27,28]:
        name=f'C_letterbox_trained_seed{seed}';folder=OUT/name;folder.mkdir()
        float_path=SOURCE/name/'embedding_fp32.onnx';quant_path=SOURCE/name/'embedding_conv_qdq.onnx'
        fgraph,fc=augment(float_path,folder/'float_conv_outputs.onnx');qgraph,qc=augment(quant_path,folder/'qdq_conv_outputs.onnx')
        assert [n.name for n in fc]==[n.name for n in qc]
        finits={t.name:numpy_helper.to_array(t) for t in fgraph.graph.initializer};qinits={t.name:numpy_helper.to_array(t) for t in qgraph.graph.initializer}
        qproducers={output:node for node in qgraph.graph.node for output in node.output};quantizers={node.input[0]:node for node in qgraph.graph.node if node.op_type=='QuantizeLinear'}
        fr=runtime(folder/'float_conv_outputs.onnx');qr=runtime(folder/'qdq_conv_outputs.onnx')
        observations={n.name:[] for n in fc};weight_checks={};clipping={n.name:[] for n in fc};witness={}
        for i,tensor in enumerate(inputs):
            fo=dict(zip([o.name for o in fr.get_outputs()],fr.run(None,{'images':tensor})))
            qo=dict(zip([o.name for o in qr.get_outputs()],qr.run(None,{'images':tensor})))
            for fnode,qnode in zip(fc,qc):
                a=fo[fnode.output[0]];b=qo[qnode.output[0]];observations[fnode.name].append(geometry(a,b))
                q=quantizers.get(qnode.output[0])
                if q is not None:
                    scale=qinits[q.input[1]];zero=qinits[q.input[2]];limits=np.iinfo(zero.dtype)
                    lo=(limits.min-zero.astype(float))*scale;hi=(limits.max-zero.astype(float))*scale
                    clipping[fnode.name].append(float(np.mean((a<lo)|(a>hi))))
                if i==0:
                    dq=qproducers[qnode.input[1]];assert dq.op_type=='DequantizeLinear'
                    quantised=qinits[dq.input[0]];scale=qinits[dq.input[1]];zero=qinits[dq.input[2]]
                    axis=next((a.i for a in dq.attribute if a.name=='axis'),1)
                    shape=[1]*quantised.ndim;shape[axis]=scale.size
                    restored=(quantised.astype(float)-zero.reshape(shape).astype(float))*scale.reshape(shape)
                    weight_checks[fnode.name]=geometry(finits[fnode.input[1]],restored)
                    witness[fnode.name]=(a,b)
        layers=[]
        for index,fnode in enumerate(fc):
            rows=observations[fnode.name];layers.append({'conv_index':index,'node':fnode.name,
             'median_relative_RMSE':float(np.median([r['relative_RMSE'] for r in rows])),
             'median_cosine':float(np.median([r['cosine'] for r in rows])),
             'median_float_outputs_outside_quant_interval':float(np.median(clipping[fnode.name])) if clipping[fnode.name] else None,
             'weight_quantisation':weight_checks[fnode.name],'sample_metrics':rows})
        drift=next((r for r in layers if r['median_relative_RMSE']>=.2),None)
        if drift is not None:
            a,b=witness[drift['node']];np.savez_compressed(folder/'first_large_drift_witness.npz',fp32=a,qdq=b)
        normal=runtime(quant_path,True,folder/'default_optimised_qdq.onnx');unfused=runtime(quant_path,False,folder/'fusion_disabled_qdq.onnx');float_normal=runtime(float_path,True)
        actual_controls=[]
        for i,tensor in enumerate(inputs):
            a=float_normal.run(None,{'images':tensor})[0];b=normal.run(None,{'images':tensor})[0];c=unfused.run(None,{'images':tensor})[0]
            actual_controls.append({'sample':i,'default_qdq_vs_float':geometry(a,b),'fusion_disabled_qdq_vs_float':geometry(a,c),'default_vs_disabled':geometry(b,c)})
        optimised_ops={mode:dict(Counter(n.op_type for n in onnx.load(folder/file).graph.node)) for mode,file in [('default','default_optimised_qdq.onnx'),('disabled','fusion_disabled_qdq.onnx')]}
        record={'condition':name,'seed':seed,'graph_sha256':{'FP32':hashlib.sha256(float_path.read_bytes()).hexdigest(),'QDQ':hashlib.sha256(quant_path.read_bytes()).hexdigest()},
                'first_conv_median_relative_RMSE_ge02':drift,'layers':layers,'same_graph_runtime_controls':actual_controls,'optimised_operator_counts':optimised_ops}
        (folder/'summary.json').write_text(json.dumps(record,indent=2));summary.append(record)
        print(json.dumps({'seed':seed,'first_large_drift_conv':None if drift is None else {'index':drift['conv_index'],'name':drift['node'],'relative_RMSE':drift['median_relative_RMSE']},
                          'training_sample0_default_cosine':actual_controls[0]['default_qdq_vs_float']['cosine'],
                          'training_sample0_no_fusion_cosine':actual_controls[0]['fusion_disabled_qdq_vs_float']['cosine']}),flush=True)
    result={'status':'TRAINING_ONLY_ACTIVATION_DIAGNOSIS_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':hashlib.sha256((ROOT/'protocol/activation_diagnosis_v1.json').read_bytes()).hexdigest(),
            'samples':samples,'conditions':summary,'no_validation_or_evaluation_images_read':True}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2))
if __name__=='__main__':main()
