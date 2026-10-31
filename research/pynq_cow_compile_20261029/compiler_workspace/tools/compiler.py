"""Independent O7 compiler helpers; never writes any predecessor directory."""
import pathlib,sys,json,hashlib,runpy,shutil,subprocess
import numpy as np
D=pathlib.Path(__file__).resolve().parents[1]
def compile_onnx(source,out):
 out=pathlib.Path(out).resolve();assert not out.exists(),'fresh output required';out.mkdir(parents=True);W=out/'compiler';W.mkdir();(W/'reports/stage_d').mkdir(parents=True);M=out/'model';shutil.copy2(D/'runtime/fixed_point.py',W/'fixed_point.py');sys.path.insert(0,str(W));oldargv=sys.argv.copy()
 try:
  for name in ('prepare_graph.py','prepare_activation.py','prepare_fixed_parameters.py'):
   text=(D/'compiler_sources'/name).read_text().replace('ROOT=pathlib.Path(__file__).resolve().parents[2]','ROOT=pathlib.Path('+repr(str(W))+')');text=text.replace("O=ROOT/'output/stage_d'/args.output_name",'O=pathlib.Path('+repr(str(M))+')').replace("M=ROOT/'output/stage_d'/args.model_name",'M=pathlib.Path('+repr(str(M))+')').replace('str(M.relative_to(ROOT))','str(M)');s=W/name;s.write_text(text);sys.argv=[str(s)]+(['--source',str(pathlib.Path(source).resolve()),'--output-name','generated'] if name=='prepare_graph.py' else ['--model-name','generated']);runpy.run_path(str(s),run_name='__main__')
 finally:sys.argv=oldargv;sys.path.remove(str(W))
 return M
def enable_integer_depthwise(model):
 sys.path.insert(0,str(D/'pc_intdw'));from fixed_point import coefficients
 M=pathlib.Path(model);p=M/'graph.json';g=json.loads(p.read_text());changed=[]
 with np.load(M/'constants.npz') as z:c={k:z[k] for k in z.files}
 with np.load(M/'fixed_parameters.npz') as z:fixed={k:z[k] for k in z.files}
 for s in g['convolutions']:
  if s['quantized'] and s['groups']==s['Cin']==s['Cout'] and s['K']==3:
   s['CPU_INT8_supported']=True;s['O7_execution']='ARM NEON INT8/INT32 fixed requant';q=s['quant'];m,shift=coefficients(float(c[q['input_scale']])*c[q['weight_scale']].astype(np.float64)/float(c[q['output_scale']]));fixed[f'mult{s["id"]}']=m;fixed[f'shift{s["id"]}']=shift;changed.append(s['id'])
 assert len(changed)==8,changed;p.write_text(json.dumps(g,indent=2));np.savez(M/'fixed_parameters.npz',**fixed);return changed
def export_program(model,size,out):
 cmd=[sys.executable,str(D/'tools/export_program.py'),'--size',str(size),'--model-dir',str(model),'--output',str(out)];subprocess.run(cmd,check=True)
