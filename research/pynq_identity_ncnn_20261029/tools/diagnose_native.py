"""Print stage boundaries and capture native crash exit without rerunning132vectors."""
from pathlib import Path
import os,sys,json,subprocess
ROOT=Path(__file__).resolve().parent
assert not (ROOT/'native_crash_diagnostic.json').exists()
code='''import faulthandler
faulthandler.enable()
from pathlib import Path
print('before_imports',flush=True)
import numpy as np
from ncnn_encoder import Encoder
root=Path.cwd()
print('before_native_create',flush=True)
encoder=Encoder(root,threads=1)
print('native_create_finished',flush=True)
with np.load(root/'vectors/old_gallery_000.npz') as a:x=a['input']
print('before_native_run',flush=True)
raw=encoder.run(x)
print('native_run_finished',raw.shape,float(raw[0]),flush=True)
encoder.close()
print('native_close_finished',flush=True)
'''
env=os.environ.copy();env['OMP_NUM_THREADS']='1';env['OPENBLAS_NUM_THREADS']='1'
result=subprocess.run([sys.executable,'-u','-B','-c',code],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
report={'status':'CAPTURED_NATIVE_VECTOR_START_EXIT','returncode':result.returncode,'stdout':result.stdout.decode(errors='replace'),
 'stderr':result.stderr.decode(errors='replace'),'full132vectors_not_rerun':True}
(ROOT/'native_crash_diagnostic.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
