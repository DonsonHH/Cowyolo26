"""Restore exact exported weights/qparams and find first full-model CPU divergence."""
from pathlib import Path
import copy, json, os
import numpy as np
import torch
import onnx, onnxruntime as ort
from onnx import helper, numpy_helper
from qat_components import *

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/qat_study')


def main():
    torch.set_num_threads(2)
    source=ROOT/'results/smoke/initial_qat_unpacked.onnx'
    graph=onnx.load(source)
    producers={s:n for n in graph.graph.node for s in n.output}
    arrays={v.name:numpy_helper.to_array(v) for v in graph.graph.initializer}
    def constant(name):
        while name not in arrays:
            node=producers[name];assert node.op_type=='Identity';name=node.input[0]
        return arrays[name]
    protocol=json.loads((ROOT/'protocol/qat_v2.json').read_text())
    base=make_encoder(protocol['source_models'][0]['path'])
    folded,_=fold_batchnorm(base);model,_=insert_quantisers(folded)
    nodes={n.name:n for n in graph.graph.node}
    tensor_map={};output_names=[]
    for name,module in model.named_modules():
        if not isinstance(module,QuantisedConvReference):continue
        weight_name='encoder.'+name+'.conv.weight'
        wq=next(n for n in graph.graph.node if n.op_type=='QuantizeLinear' and n.input[0]==weight_name)
        prefix=wq.name.split('/weight_quant/')[0]
        wdq=next(n for n in graph.graph.node if n.op_type=='DequantizeLinear' and n.input[0]==wq.output[0])
        conv=next(n for n in graph.graph.node if n.op_type=='Conv' and n.input[1]==wdq.output[0])
        module.conv.weight.data.copy_(torch.from_numpy(constant(weight_name).copy()))
        module.conv.bias.data.copy_(torch.from_numpy(constant(conv.input[2]).copy()))
        for field in ['input_quant','weight_quant','output_quant']:
            fq=getattr(module,field);q=nodes[prefix+'/'+field+'/QuantizeLinear']
            scale=torch.from_numpy(np.asarray(constant(q.input[1])).copy()).reshape(-1)
            zero=torch.from_numpy(np.asarray(constant(q.input[2])).astype(np.int32)).reshape(-1)
            fq.scale.resize_(scale.shape).copy_(scale);fq.zero_point.resize_(zero.shape).copy_(zero)
            dq=next(n for n in graph.graph.node if n.op_type=='DequantizeLinear' and n.input[0]==q.output[0])
            tensor_map[name+'.'+field]={'before':q.input[0],'after':dq.output[0]}
            output_names.extend([q.input[0],dq.output[0]])
    quant_mode(model,fake=True,observe=False);model.eval()
    saved=np.load(ROOT/'results/smoke/export_parity_vectors.npz')
    x=saved['inputs'][3:4]
    with torch.no_grad():restored=torch.nn.functional.normalize(model(torch.from_numpy(x)),dim=1).numpy()
    assert np.array_equal(restored,saved['torch'][3:4]),'Restored graph does not reproduce saved PyTorch failure'
    output_names=list(dict.fromkeys(output_names))
    augmented=copy.deepcopy(graph);del augmented.graph.output[:]
    augmented.graph.output.extend([helper.make_tensor_value_info(n,onnx.TensorProto.FLOAT,None) for n in output_names])
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    runtime=ort.InferenceSession(augmented.SerializeToString(),sess_options=options,providers=['CPUExecutionProvider'])
    values=dict(zip(output_names,runtime.run(None,{'images':x})))
    results=[]
    for mkldnn in [True,False]:
        torch.backends.mkldnn.enabled=mkldnn
        trace=[];handles=[]
        for name,module in model.named_modules():
            if name not in tensor_map:continue
            def hook(mod,arguments,output,label=name):
                before=arguments[0].detach().numpy().copy();after=output.detach().numpy().copy()
                item={'module':label}
                for stage,tensor in [('before',before),('after',after)]:
                    reference=values[tensor_map[label][stage]]
                    item[stage+'_different_elements']=int((tensor!=reference).sum())
                    item[stage+'_max_absolute_error']=float(np.max(np.abs(tensor-reference)))
                trace.append(item)
            handles.append(module.register_forward_hook(hook))
        with torch.no_grad():output=torch.nn.functional.normalize(model(torch.from_numpy(x)),dim=1).numpy()
        for h in handles:h.remove()
        differences=[r for r in trace if r['after_max_absolute_error']>1e-6]
        results.append({'torch_mkldnn':mkldnn,'first_quantised_output_difference':differences[0] if differences else None,
                        'embedding_max_absolute_error':float(np.max(np.abs(output-saved['packed'][3:4]))),
                        'all_quantiser_cases':trace})
    save(ROOT/'results/remaining_drift_probe.json',{'status':'EXACT_RESTORE_AND_BACKEND_CONTROL_COMPLETE',
         'job_id':os.environ['SLURM_JOB_ID'],'training_vector':3,'exact_restore_saved_torch_output':True,'conditions':results})
    print(json.dumps([{k:v for k,v in r.items() if k!='all_quantiser_cases'} for r in results]),flush=True)


if __name__=='__main__':main()
