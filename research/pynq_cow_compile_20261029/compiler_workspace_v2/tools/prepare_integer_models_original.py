import pathlib,json,shutil,numpy as np,sys
R=pathlib.Path(__file__).resolve().parents[2];D=R/'yolo26_optimization_7';sys.path.insert(0,str(D/'runtime_fast'))
from fixed_point import coefficients
dest=D/'pc_intdw'
if not dest.exists():
 shutil.copytree(D/'pc_runtime_fast',dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 p=dest/'hybrid_executor.py';s=p.read_text().replace("spec['FPGA_supported']","(spec['FPGA_supported'] or spec.get('CPU_INT8_supported',False))").replace("s['FPGA_supported']","(s['FPGA_supported'] or s.get('CPU_INT8_supported',False))");p.write_text(s)
for size in (192,224,256):
 source=D/('r%d_fullptq/model'%size)
 if not source.exists():continue
 target=D/('r%d_intdw/model'%size)
 if target.exists():continue
 shutil.copytree(source,target)
 g=json.loads((target/'graph.json').read_text());params={}
 with np.load(target/'fixed_parameters.npz') as a:params.update({k:a[k] for k in a.files})
 with np.load(target/'constants.npz') as c:
  for s in g['convolutions']:
   if s['groups']==s['Cin']==s['Cout'] and s['K']==3:
    s['CPU_INT8_supported']=True;s['O7_execution']='ARM NEON INT8/INT32 fixed requant; native packed layout'
    q=s['quant'];m,shift=coefficients(float(c[q['input_scale']])*c[q['weight_scale']].astype(np.float64)/float(c[q['output_scale']]))
    params['mult%d'%s['id']]=m;params['shift%d'%s['id']]=shift
 np.savez(target/'fixed_parameters.npz',**params);(target/'graph.json').write_text(json.dumps(g,indent=2))
 print('O7_INTDW_MODEL',size,sum(s.get('CPU_INT8_supported',False) for s in g['convolutions']))
evaluation=(D/'evaluate_release.py').read_text().replace("D/'pc_runtime_fast'","D/'pc_intdw'");(D/'evaluate_intdw.py').write_text(evaluation)
