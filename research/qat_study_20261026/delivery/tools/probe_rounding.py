"""Exact-input PyTorch/ONNX quantiser comparison; only first calibration training image."""
from pathlib import Path
import json, os, sys
import numpy as np
import torch
import onnx, onnxruntime as ort
from onnx import helper, numpy_helper
from PIL import Image
from qat_components import save

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'qat_study'
sys.path.insert(0,str(PROJECT/'identity_training/tools'))
from training_primitives import BodyTransform


def main():
    torch.set_num_threads(2)
    path=ROOT/'results/smoke/initial_qat_unpacked.onnx'
    model=onnx.load(path)
    producers={s:n for n in model.graph.node for s in n.output}
    arrays={v.name:numpy_helper.to_array(v) for v in model.graph.initializer}
    quantisers=[n for n in model.graph.node if n.op_type=='QuantizeLinear']
    outputs={}
    for node in quantisers:
        dequant=next(n for n in model.graph.node if n.op_type=='DequantizeLinear' and n.input[0]==node.output[0])
        for name in [*node.input,dequant.output[0]]:
            if name not in arrays:
                outputs[name]=helper.make_tensor_value_info(name,onnx.TensorProto.FLOAT,None)
    # Zero point outputs are integer, which can be shared through Identity.
    def constant(name):
        while name not in arrays:
            n=producers[name]; assert n.op_type=='Identity'; name=n.input[0]
        return arrays[name]
    zero_names={n.input[2] for n in quantisers}
    for name in list(outputs):
        if name in zero_names:
            outputs[name]=helper.make_tensor_value_info(name,helper.np_dtype_to_tensor_dtype(constant(name).dtype),None)
    del model.graph.output[:];model.graph.output.extend(outputs.values())
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    runtime=ort.InferenceSession(model.SerializeToString(),sess_options=options,providers=['CPUExecutionProvider'])
    probe_index=int(os.environ.get('QAT_PROBE_INDEX','0'))
    row=json.loads((PROJECT/'deployment_audit/results/export_audit/ptq_calibration_training_only.json').read_text())[probe_index]
    assert row['split']=='train'
    with Image.open(PROJECT/'identity_training'/row['relative_path']) as im:
        value=BodyTransform()(im.convert('RGB')).numpy()[None]
    got=runtime.run(None,{'images':value});values={**arrays,**dict(zip(outputs,got))}
    cases=[]
    for node in quantisers:
        dequant=next(n for n in model.graph.node if n.op_type=='DequantizeLinear' and n.input[0]==node.output[0])
        x=values[node.input[0]]; scale=values[node.input[1]]; zero=values[node.input[2]]
        expected=values[dequant.output[0]]
        if scale.size>1:
            axis=next(int(a.i) for a in node.attribute if a.name=='axis')
            actual=torch.fake_quantize_per_channel_affine(torch.from_numpy(x.copy()),torch.from_numpy(scale.copy()),
                     torch.from_numpy(zero.astype(np.int32)),axis,-128,127).numpy()
            kind='weight';shape=[1]*x.ndim;shape[axis]=len(scale)
            s=scale.reshape(shape);z=zero.reshape(shape);lo,hi=-128,127
        else:
            actual=torch.fake_quantize_per_tensor_affine(torch.from_numpy(x.copy()),float(scale.reshape(-1)[0]),
                     int(zero.reshape(-1)[0]),0,255).numpy()
            kind='activation';s=scale;z=zero;lo,hi=0,255
        multiplication=(np.clip(np.rint(x*(np.float32(1)/s))+z,lo,hi)-z)*s
        division=(np.clip(np.rint(x/s)+z,lo,hi)-z)*s
        difference=actual!=expected
        ts=torch.from_numpy(np.asarray(s).copy());tz=torch.from_numpy(np.asarray(z).copy())
        explicit_division=((torch.clamp(torch.round(torch.from_numpy(x.copy())/ts)+tz,lo,hi)-tz)*ts).numpy()
        cases.append({'node':node.name,'kind':kind,'shape':list(x.shape),'different_elements':int(difference.sum()),
                      'elements':x.size,'max_absolute_difference':float(np.max(np.abs(actual-expected))),
                      'torch_vs_multiply_difference_elements':int((actual!=multiplication).sum()),
                      'torch_vs_divide_difference_elements':int((actual!=division).sum()),
                      'onnx_vs_multiply_difference_elements':int((expected!=multiplication).sum()),
                      'onnx_vs_divide_difference_elements':int((expected!=division).sum()),
                      'torch_explicit_division_vs_onnx_difference_elements':int((explicit_division!=expected).sum())})
    output_name='rounding_probe.json' if probe_index==0 else f'rounding_probe_training{probe_index}.json'
    save(ROOT/'results'/output_name,{'job_id':os.environ['SLURM_JOB_ID'],'row':row,'cases':cases,'training_index':probe_index,
         'quantiser_count':len(cases),'weight_differing_cases':sum(r['kind']=='weight' and r['different_elements']>0 for r in cases),
         'activation_differing_cases':sum(r['kind']=='activation' and r['different_elements']>0 for r in cases)})
    print(json.dumps({'cases':len(cases),'first_differences':[r for r in cases if r['different_elements']][:10]}),flush=True)


if __name__=='__main__':main()
