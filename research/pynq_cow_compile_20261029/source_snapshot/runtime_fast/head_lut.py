"""Fuse final classification DQ/reshape/concat/sigmoid into 3 exact-code float LUTs."""
import numpy as np,collections,os
def optimize(ex):
 if os.environ.get('O6_HEAD_LUT_DISABLE')=='1':return
 if ex.head_nets:raise ValueError('LUT research requires all three classification outputs quantized')
 target=next(n for n in ex.graph['nodes'] if n['name']=='/model.23/Sigmoid')
 additions=[];parts=[];proof=[]
 for scale in range(3):
  spec=next(s for s in ex.specs.values() if s['name']=='/model.23/one2one_cv3.%d/one2one_cv3.%d.2/Conv'%(scale,scale))
  assert spec['FPGA_supported'] and spec['Cout']==80
  q=spec['quant'];codes=np.arange(256,dtype=np.uint8).view(np.int8)
  x=(codes.astype(np.float32)-np.float32(ex.constants[q['output_zp']]))*np.float32(ex.constants[q['output_scale']])
  table=np.float32(1)/(np.float32(1)+np.exp(-np.maximum(x,np.float32(-80))))
  extreme=x<-80
  if np.any(extreme):e=np.exp(x[extreme]);table[extreme]=e/(np.float32(1)+e)
  key='_o6_cls_sigmoid_table_%d'%scale;shape='_o6_cls_shape_%d'%scale;ex.constants[key]=table;ex.constants[shape]=np.array([1,80,-1],np.int64)
  lookup='_o6_cls_lookup_%d'%scale;flat='_o6_cls_flat_%d'%scale
  additions.extend([dict(name=lookup,op='FloatLookup',inputs=[q['output'],key],outputs=[lookup],attrs={}),dict(name=flat,op='Reshape',inputs=[lookup,shape],outputs=[flat],attrs={})]);parts.append(flat)
  proof.append(dict(scale=scale,codes=256,input_scale=float(ex.constants[q['output_scale']]),input_zp=int(ex.constants[q['output_zp']]),formula='same float32 stable sigmoid applied exhaustively to all quantized codes'))
 additions.append(dict(name=target['name'],op='Concat',inputs=parts,outputs=target['outputs'],attrs={'axis':2}))
 nodes=[]
 for n in ex.graph['nodes']:nodes.extend(additions if n is target else [n])
 required=dict(ex.required_inputs)
 for n in additions:required[n['name']]=list(n['inputs'])
 producers={o:n for n in nodes for o in n['outputs']};needed=set();todo=[ex.graph['output']]
 while todo:
  name=todo.pop();n=producers.get(name)
  if n is None or n['name'] in needed:continue
  needed.add(n['name']);todo.extend(required[n['name']])
 old_count=len(nodes);nodes=[n for n in nodes if n['name'] in needed]
 ex.graph['nodes']=nodes;ex.producers={o:n for n in nodes for o in n['outputs']};ex.required_inputs={n['name']:required[n['name']] for n in nodes}
 ex.use_counts=collections.Counter(i for values in ex.required_inputs.values() for i in values if i)
 ex.o6_lut_audit=dict(code_checks=proof,removed_dead_nodes=old_count-len(nodes),new_ops='3 float LUT + 3 reshape + concat; detector heads remain executed')
