"""Frozen full-PTQ ONNX -> integer depthwise model -> native static graph."""
import pathlib,argparse,json,hashlib,sys
D=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(D/'tools'));from compiler import compile_onnx,enable_integer_depthwise,export_program
p=argparse.ArgumentParser();p.add_argument('--size',type=int,choices=(192,224,256),default=224);p.add_argument('--candidate');p.add_argument('--source',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();source=a.source or D/(a.candidate or f'r{a.size}_fullptq')/'allconv_int8.onnx';M=compile_onnx(source,a.output);ids=enable_integer_depthwise(M);export_program(M,a.size,a.output/'program');record=dict(size=a.size,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),integer_depthwise_ids=ids,program_sha256=hashlib.sha256((a.output/'program/graph.bin').read_bytes()).hexdigest(),training=False)
assert record['program_sha256']==hashlib.sha256((D/f'program_r{a.size}/graph.bin').read_bytes()).hexdigest(),'O8 math-preservation gate: rebuilt graph differs from frozen graph'
import shutil
sys.path.insert(0,str(D/'compiler'));from resident_plan import make,write
T=a.output/'plan_input'/f'program_r{a.size}';T.mkdir(parents=True)
for name in ('graph.bin','program.json'):shutil.copy2(a.output/'program'/name,T/name)
record['resident_plan_SHA256']=write(make(T.parent,a.size,'all'),a.output/'resident_plan_all');assert record['resident_plan_SHA256']==hashlib.sha256((D/f'plans/r{a.size}_all/resident_plan.bin').read_bytes()).hexdigest()
(a.output/'recompile_result.json').write_text(json.dumps(record,indent=2));print('O8_RECOMPILE_GRAPH_AND_PLAN_IDENTICAL',record)
