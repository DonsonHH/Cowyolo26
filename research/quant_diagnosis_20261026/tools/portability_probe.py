from pathlib import Path
import hashlib,json,os,platform
import numpy as np
import onnxruntime as ort
from PIL import Image,ImageOps,__version__ as pillow_version
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/quant_diagnosis')
OUT=ROOT/'results/portability_probe';OUT.mkdir(parents=True,exist_ok=False)
p=json.loads((ROOT/'protocol/future_comparison_frozen.json').read_text())
condition=next(r for r in p['conditions'] if r['seed']==27 and r['method']==p['selected_recipe'])
path=ROOT/'holdout_data/2023Aug14/025/00000_1.jpg'
with Image.open(path) as im:im=ImageOps.pad(im.convert('RGB'),(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127),centering=(.5,.5))
pixels=np.asarray(im);x=pixels.transpose(2,0,1).astype(np.float32)/np.float32(255)
x=(x-np.array([.485,.456,.406],np.float32)[:,None,None])/np.array([.229,.224,.225],np.float32)[:,None,None]
x=np.ascontiguousarray(x[None]);outputs={}
for mode,level in [('default',ort.GraphOptimizationLevel.ORT_ENABLE_ALL),('disabled',ort.GraphOptimizationLevel.ORT_DISABLE_ALL)]:
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1;options.graph_optimization_level=level
    runtime=ort.InferenceSession(condition['model_path'],sess_options=options,providers=['CPUExecutionProvider'])
    outputs[mode]=runtime.run(None,{'images':x})[0][0]
np.savez_compressed(OUT/'exact_input_and_outputs.npz',input=x,resized_pixels=pixels,default=outputs['default'],disabled=outputs['disabled'])
record={'job_id':os.environ['SLURM_JOB_ID'],'source_image':str(path.relative_to(ROOT)),
        'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'input_tensor_sha256':hashlib.sha256(x.tobytes()).hexdigest(),
        'resized_pixel_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'pillow':pillow_version,'numpy':np.__version__,
        'onnxruntime':ort.__version__,'platform':platform.platform(),'model_sha256':condition['model_sha256'],
        'Linux_default_vs_disabled_max_feature_error':float(np.abs(outputs['default']-outputs['disabled']).max()),
        'purpose':'Post-evaluation numerical control only; no model, threshold or selected recipe changes'}
(OUT/'summary.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2),flush=True)
