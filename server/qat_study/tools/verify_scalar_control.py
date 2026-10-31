"""Compare unchanged values and exact reference execution before/after scalar shape fix."""
from pathlib import Path
import json, sys
import numpy as np
from PIL import Image, ImageOps
BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'deployment_audit_20261026/local_dependencies'))
import onnxruntime as ort
from onnx_canonical import canonicalise_activation_scalars
ROOT = Path(__file__).resolve().parents[1]
source = ROOT/'results/failed_smoke_initial_packed.onnx'
fixed = ROOT/'results/failed_smoke_scalar_control.onnx'
record = canonicalise_activation_scalars(source,fixed)
photo = BASE/'identity_training_20261026/delivery/data/2023Aug15/049/00011_1.jpg'
with Image.open(photo) as im:
    im = ImageOps.pad(im.convert('RGB'), (224,224),method=Image.Resampling.BILINEAR,color=(127,127,127))
    value = np.asarray(im).astype(np.float32).transpose(2,0,1)/np.float32(255)
    value = ((value-np.array([.485,.456,.406],dtype=np.float32)[:,None,None])/
             np.array([.229,.224,.225],dtype=np.float32)[:,None,None])[None]
def runtime(path,optimise):
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL if optimise else ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
before=runtime(source,False).run(None,{'images':value})[0]
after=runtime(fixed,False).run(None,{'images':value})[0]
assert np.array_equal(before,after)
try:
    runtime(source,True)
    old_error=None
except Exception as e:
    old_error=str(e)
assert old_error and 'must be a scalar' in old_error
new_output=runtime(fixed,True).run(None,{'images':value})[0]
np.savez_compressed(ROOT/'results/scalar_control_vectors.npz',input=value,before=before,after=after,optimised=new_output)
result={'status':'PASS_SINGLE_TRAIN_VECTOR_SCALAR_CONTROL', 'canonicalisation':record,
        'reference_before_after_bitwise_equal':True,'old_optimisation_error':old_error,
        'new_optimisation_initialises':True,'new_optimisation_max_output_difference':float(np.max(np.abs(after-new_output)))}
(ROOT/'results/scalar_control.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='canonicalisation'}))
