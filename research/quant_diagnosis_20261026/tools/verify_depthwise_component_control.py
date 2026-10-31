"""Independent direct depthwise stencil on saved real diagnostic tensors."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'deployment_audit_20261026/local_dependencies'))
import numpy as np
x=np.load(ROOT/'results/first_depthwise_component_witness.npz')
record=json.loads((ROOT/'results/first_depthwise_component_controls.json').read_text());attrs=record['attributes']
def direct_stencil(value,weight,bias):
    pads=attrs['pads'];stride=attrs['strides'];kernel=attrs['kernel_shape']
    a=np.pad(value,((0,0),(0,0),(pads[0],pads[2]),(pads[1],pads[3])))
    shape=[value.shape[0],value.shape[1],(a.shape[2]-kernel[0])//stride[0]+1,(a.shape[3]-kernel[1])//stride[1]+1]
    out=np.broadcast_to(bias[None,:,None,None],shape).copy()
    for ky in range(kernel[0]):
        for kx in range(kernel[1]):
            out+=a[:,:,ky:ky+shape[2]*stride[0]:stride[0],kx:kx+shape[3]*stride[1]:stride[1]]*weight[:,0,ky,kx][None,:,None,None]
    return out
conditions=[('float_reconstruction','float_input','float_weights','float_bias'),
            ('only_actual_quantised_input','quant_input','float_weights','float_bias'),
            ('only_quantised_weights','float_input','quant_weights','float_bias'),
            ('only_quantised_bias','float_input','float_weights','quant_bias'),
            ('all_quantised_reconstruction','quant_input','quant_weights','quant_bias')]
checks=[]
for name,inputs,weights,bias in conditions:
    out=direct_stencil(x[inputs],x[weights],x[bias]);ratio=float(np.linalg.norm(out-x['float_output'])/np.linalg.norm(x['float_output']))
    expected=next(r['relative_RMSE_to_float'] for r in record['controls'] if r['condition']==name)
    assert abs(ratio-expected)<1e-10
    checks.append({'condition':name,'relative_RMSE_to_float':ratio,'independent_stencil_agreement':True})
result={'status':'PASS','real_training_crop':record['training_crop'],'scope':'One-crop first-depthwise input/weight/bias intervention arithmetic; not a complete causal allocation across all layers','controls':checks}
(ROOT/'results/depthwise_independent_verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
