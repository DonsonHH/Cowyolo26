from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'deployment_audit_20261026/local_dependencies'))
import onnxruntime as ort,numpy as np
from PIL import Image,ImageOps,__version__ as pillow_version
folder=ROOT/'results/portability_probe';status=(ROOT/'results/portability_server_status.txt').read_text()
for file in ['summary.json','exact_input_and_outputs.npz']:assert hashlib.sha256((folder/file).read_bytes()).hexdigest() in status
record=json.loads((folder/'summary.json').read_text());data=np.load(folder/'exact_input_and_outputs.npz')
with Image.open(ROOT/'delivery'/record['source_image']) as im:im=ImageOps.pad(im.convert('RGB'),(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127),centering=(.5,.5))
pixels=np.asarray(im);x=pixels.transpose(2,0,1).astype(np.float32)/np.float32(255)
x=(x-np.array([.485,.456,.406],np.float32)[:,None,None])/np.array([.229,.224,.225],np.float32)[:,None,None]
x=np.ascontiguousarray(x[None]);same=np.array_equal(x,data['input'])
path=ROOT/'delivery/results/mixed/front_and_depthwise_fp/C_letterbox_trained_seed27/embedding_mixed_qdq.onnx'
assert hashlib.sha256(path.read_bytes()).hexdigest()==record['model_sha256']
results=[]
for mode,level in [('default',ort.GraphOptimizationLevel.ORT_ENABLE_ALL),('disabled',ort.GraphOptimizationLevel.ORT_DISABLE_ALL)]:
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1;options.graph_optimization_level=level
    runtime=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
    for input_name,tensor in [('Windows_preprocessed',x),('Linux_exact_input',data['input'])]:
        actual=runtime.run(None,{'images':tensor})[0][0]
        results.append({'Windows_optimisation':mode,'input':input_name,
             'max_feature_error_to_Linux_default':float(np.abs(actual-data['default']).max()),
             'max_feature_error_to_Linux_disabled':float(np.abs(actual-data['disabled']).max())})
output={'status':'NUMERICAL_PORTABILITY_CONTROL_COMPLETE','local_pillow':pillow_version,
        'input_tensors_bitwise_equal':same,'resized_pixels_bitwise_equal':np.array_equal(pixels,data['resized_pixels']),
        'max_preprocessed_input_error':float(np.abs(x-data['input']).max()),'comparisons':results,
        'model_or_threshold_changed':False,'interpretation':'A numerical diagnostic on an already evaluated gallery image; retain differences rather than relax tolerance or alter holdout selection'}
(ROOT/'results/portability_control_verification.json').write_text(json.dumps(output,indent=2))
print(json.dumps(output,indent=2))
