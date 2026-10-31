"""Real graph/real training crop numerical failure harness, exit2 means drift."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'deployment_audit_20261026/local_dependencies'))
import numpy as np
import onnxruntime as ort
from PIL import Image,ImageOps

def session(path):
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
source=PROJECT/'deployment_audit_20261026/delivery/results/export_audit'
row=json.loads((source/'ptq_calibration_training_only.json').read_text())[0]
assert row['split']=='train'
image=PROJECT/'identity_training_20261026/delivery'/row['relative_path']
assert hashlib.sha256(image.read_bytes()).hexdigest()==row['sha256']
with Image.open(image) as im:im=ImageOps.pad(im.convert('RGB'),(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127),centering=(.5,.5))
value=np.asarray(im).transpose(2,0,1).astype(np.float32)/np.float32(255)
value=(value-np.array([.485,.456,.406],np.float32)[:,None,None])/np.array([.229,.224,.225],np.float32)[:,None,None]
folder=source/'C_letterbox_trained_seed26'
a=session(folder/'embedding_fp32.onnx').run(None,{'images':np.ascontiguousarray(value[None])})[0][0]
b=session(folder/'embedding_conv_qdq.onnx').run(None,{'images':np.ascontiguousarray(value[None])})[0][0]
cos=float(np.dot(a.astype(float),b.astype(float))/(np.linalg.norm(a.astype(float))*np.linalg.norm(b.astype(float))))
record={'status':'REPRODUCED_VECTOR_DRIFT' if cos<.99 else 'NO_LARGE_DRIFT_ON_THIS_SAMPLE','training_image':row['relative_path'],
        'training_image_sha256':row['sha256'],'FP32_vs_QDQ_cosine':cos,'maximum_feature_error':float(np.abs(a-b).max()),
        'engineering_numerical_signal':'Cosine<0.99 on the same crop is a diagnostic drift trigger, not a recognition accuracy threshold',
        'graph_sha256':{name:hashlib.sha256((folder/name).read_bytes()).hexdigest() for name in ['embedding_fp32.onnx','embedding_conv_qdq.onnx']},
        'no_validation_or_evaluation_image_used':True}
(ROOT/'results').mkdir(exist_ok=True);(ROOT/'results/training_vector_repro.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
raise SystemExit(2 if cos<.99 else 0)
