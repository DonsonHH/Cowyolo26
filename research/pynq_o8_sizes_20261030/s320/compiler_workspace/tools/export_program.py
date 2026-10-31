"""Export a frozen optimized graph, exact constant bytes and observed static shapes."""
import os,sys,pathlib,json,argparse,struct,collections
os.environ['OMP_NUM_THREADS']='4';sys.dont_write_bytecode=True
D=pathlib.Path(__file__).resolve().parents[1];R=D.parent;sys.path.insert(0,str(D/'pc_intdw'))
import numpy as np,cv2,torch
from hybrid_executor import YOLOHybridExecutor
from integer_backend import TorchIntegerBackend
sys.path.insert(0,str(D/'runtime_fast'))
from board_runtime import preprocess
p=argparse.ArgumentParser();p.add_argument('--size',type=int,required=True);p.add_argument('--model-dir',type=pathlib.Path);p.add_argument('--output',type=pathlib.Path);a=p.parse_args();M=(a.model_dir or D/('r%d_intdw/model'%a.size)).resolve();O=(a.output or D/('program_r%d'%a.size)).resolve();O.mkdir(parents=True,exist_ok=True);assert not any(O.iterdir()),'refuse overwrite nonempty program';torch.set_num_threads(4);cv2.setNumThreads(4)
ex=YOLOHybridExecutor(M,TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)
# Apply the same exact integer routing as the accepted board runtime.
from integer_graph import optimize_integer_routes
optimize_integer_routes(ex)
from head_lut import optimize
# The PC constructor already fused the class head; do not apply that fusion twice.
captured={}
image=cv2.imread(str(D/'test_images/bus.jpg'));x=preprocess(image,a.size)
def capture(name,v,n):captured[name]=(tuple(v.shape),v.dtype)
raw=ex.run(x,capture);np.save(O/'pc_initial_raw.npy',raw)
nodes=ex.graph['nodes'];producers={o:n for n in nodes for o in n['outputs']};constants=dict(ex.constants)
for n in nodes:
 if n['op']=='SiLU':
  dq=producers.get(n['inputs'][0])
  if dq and dq['op']=='DequantizeLinear':
   match=next(s for s in ex.specs.values() if s['quantized'] and s['quant']['output']==dq['inputs'][0]);key='_o7_silu_%d'%match['id'];constants[key]=ex.activation_tables['silu%d'%match['id']]
   n['op']='FloatLookup';n['inputs']=[dq['inputs'][0],key]
# Recompute DCE after float-lookup substitution.
prod={o:n for n in nodes for o in n['outputs']};live=set()
def keep(name):
 n=prod.get(name)
 if n is None or n['name'] in live:return
 live.add(n['name'])
 for i in n['inputs']:keep(i)
keep(ex.graph['output']);nodes=[n for n in nodes if n['name'] in live]
allnames=set(constants)|set(captured)|{ex.graph['input']}
for n in nodes:allnames.update(n['inputs']);allnames.update(n['outputs'])
allnames.discard('');names=sorted(allnames);ids={n:i for i,n in enumerate(names)}
dtypes={np.dtype('float32'):1,np.dtype('uint8'):2,np.dtype('int8'):3,np.dtype('int32'):6,np.dtype('int64'):7,np.dtype('uint32'):12,np.dtype('bool'):9}
shapes={k:(v.shape,v.dtype) for k,v in constants.items()};shapes.update(captured);shapes[ex.graph['input']]=(x.shape,x.dtype)
for name in names:assert name in shapes,('missing static tensor',name)
opnames=['QuantConv','Depthwise','Identity','Int8Lookup','FloatLookup','QuantizeLinear','DequantizeLinear','SiLU','Add','Sub','Mul','Div','Concat','Split','Reshape','Transpose','MatMul','Softmax','MaxPool','Resize','Slice','ReduceMax','TopK','Unsqueeze','Expand','GatherElements','Flatten','Cast','Mod','Sigmoid']
opcodes={n:i+1 for i,n in enumerate(opnames)}
compiled=[]
for n in nodes:
 op=n['op'];attrs=n['attrs'];inputs=list(n['inputs']);extra=[]
 if op=='QuantConv':
  s=ex.specs[n['conv_id']];q=s['quant'];is_dw=s.get('CPU_INT8_supported',False);op='Depthwise' if is_dw else op
  if not is_dw:assert ((min(32,s['Cout'])+15)//16)*((s['Cin']+7)//8)*s['K']**2<=512,('core0x60004 weight bank capacity',s['id'])
  for key,value in (('_o7_mult%d'%s['id'],ex.fixed_parameters[s['id']][0]),('_o7_shift%d'%s['id'],ex.fixed_parameters[s['id']][1])):
   constants[key]=value
  # Fixed parameter tensor identifiers are appended below after graph processing.
  mode=2 if s['id'] in ex.activation_fusion else 1;lutkey='_o7_activation%d'%s['id'];constants[lutkey]=ex.activation_tables['activation%d'%s['id']] if mode==2 else np.zeros(256,np.int8)
  extra=[s['id'],s['Cin'],s['Cout'],s['K'],s['stride'],s['padding'],int(constants[q['input_zp']]),int(constants[q['weight_zp']].reshape(-1)[0]),int(constants[q['output_zp']]),mode]
  inputs=[q['input'],q['weight'],q['bias'],'_o7_mult%d'%s['id'],'_o7_shift%d'%s['id'],lutkey]
  if not is_dw:
   key='_o7_packed%d'%s['id'];constants[key]=np.load(M/'packed_weights.npz')['conv%d'%s['id']];inputs.append(key)
 elif op in ('Concat','Split','Softmax','GatherElements','Flatten'):extra=[attrs.get('axis',-1 if op in ('Softmax',) else 0)]
 elif op=='Transpose':extra=attrs.get('perm',list(reversed(range(len(shapes[inputs[0]][0])))))
 elif op=='MaxPool':extra=[attrs['kernel_shape'][0],attrs.get('pads',[0])[0],attrs.get('strides',[1])[0]]
 elif op=='ReduceMax':extra=[int(attrs.get('keepdims',1))]+attrs.get('axes',list(range(len(shapes[inputs[0]][0]))))
 elif op=='TopK':extra=[attrs.get('axis',-1),attrs.get('largest',1)]
 elif op=='Cast':extra=[attrs['to']]
 compiled.append(dict(name=n['name'],op=op,inputs=inputs,outputs=n['outputs'],attrs=extra))
for k,v in constants.items():shapes[k]=(v.shape,v.dtype)
names=sorted(set(names)|set(constants));ids={n:i for i,n in enumerate(names)}
with (O/'graph.bin').open('wb') as f:
 def ints(v):f.write(struct.pack('<'+'i'*len(v),*v))
 ints([0x3747504f,len(names),len(compiled),ids[ex.graph['input']],ids[ex.graph['output']]])
 for name in names:
  shape,typ=shapes[name];assert len(shape)<=6;(dtype,)=dtypes[typ],
  ints([dtype,len(shape)]+list(shape)+[1]*(6-len(shape)))
  value=np.ascontiguousarray(constants[name]).tobytes() if name in constants else b'';ints([len(value)]);f.write(value)
 for n in compiled:
  ins=[ids[k] if k else -1 for k in n['inputs']];outs=[ids[k] for k in n['outputs']];atr=n['attrs'];ints([opcodes[n['op']],len(ins),len(outs),len(atr)]+ins+outs+atr)
metadata=dict(size=a.size,input_id=ids[ex.graph['input']],output_id=ids[ex.graph['output']],names=names,shapes={k:[list(v[0]),str(v[1])] for k,v in shapes.items()},nodes=compiled,ops=dict(collections.Counter(n['op'] for n in compiled)),source_model=str(M),math='94 exact PL +8 fixed INT8 depthwise; common native float ops introduced by O7 engine require final verification/evaluation')
(O/'program.json').write_text(json.dumps(metadata,indent=2));print('O7_PROGRAM_EXPORTED',a.size,len(compiled),metadata['ops'])
