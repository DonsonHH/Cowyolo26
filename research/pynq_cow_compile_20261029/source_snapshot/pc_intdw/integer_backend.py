"""Fast PC integer Golden: integer-valued FP64 Conv is exact under its proven bound."""
import numpy as np,torch
import torch.nn.functional as F
class TorchIntegerBackend:
    output_kind='int32'
    def __init__(self):self.weights={}
    def execute(self,x,w,b,spec,constants):
        q=spec['quant'];zx=int(constants[q['input_zp']]);wz=constants[q['weight_zp']].astype(np.int64).reshape(-1)
        if spec['id'] not in self.weights:
            wc=w.astype(np.int64)-wz.reshape(-1,1,1,1)
            bound=255*np.abs(wc).reshape(w.shape[0],-1).sum(1)+np.abs(b.astype(np.int64))
            assert np.all(bound<2**53),'FP64 would not exactly represent the integer sum'
            self.weights[spec['id']]=(torch.from_numpy(wc.astype(np.float64)),torch.from_numpy(b.astype(np.float64)))
        weights,bias=self.weights[spec['id']]
        with torch.inference_mode():
            inp=torch.from_numpy(np.ascontiguousarray(x)).to(torch.float64).sub_(zx)
            result=F.conv2d(inp,weights,bias,stride=spec['stride'],padding=spec['padding'],groups=spec['groups']).numpy()[0]
        assert result.min()>=-2**31 and result.max()<2**31
        return result.astype(np.int32)
