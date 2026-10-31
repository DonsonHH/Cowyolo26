import sys,pathlib,json,hashlib,time,collections,argparse
import numpy as np,onnx
from onnx import numpy_helper,helper,TensorProto
ROOT=pathlib.Path('/share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_compile_20261030/results/qualification/compiled/compiler')
parser=argparse.ArgumentParser();parser.add_argument('--source',default='model/stage_b/yolo26n_int8_candidate.onnx');parser.add_argument('--output-name',default='model');args=parser.parse_args()
O=pathlib.Path('/share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_compile_20261030/results/qualification/compiled/model');O.mkdir(parents=True,exist_ok=True)
M=ROOT/args.source
model=onnx.shape_inference.infer_shapes(onnx.load(M),strict_mode=True,data_prop=True)
onnx.checker.check_model(model)
constants={a.name:numpy_helper.to_array(a).copy() for a in model.graph.initializer}
producer={o:n for n in model.graph.node for o in n.output}
consumers=collections.defaultdict(list)
for n in model.graph.node:
    for i in n.input:consumers[i].append(n)
shapes={v.name:{'shape':[d.dim_value for d in v.type.tensor_type.shape.dim],
                'dtype':TensorProto.DataType.Name(v.type.tensor_type.elem_type)}
        for v in list(model.graph.value_info)+list(model.graph.input)+list(model.graph.output)}
def attrs(node):
    result={a.name:helper.get_attribute_value(a) for a in node.attribute}
    return {k:v.decode() if isinstance(v,bytes) else list(v) if isinstance(v,(list,tuple)) else v for k,v in result.items()}
def dq(x,s,z,axis=1):
    s=np.asarray(s,dtype=np.float32);z=np.asarray(z)
    if s.ndim==1 and s.size>1:
        shape=[1]*x.ndim;shape[axis]=len(s);s=s.reshape(shape);z=z.reshape(shape)
    return (x.astype(np.float32)-z.astype(np.float32))*s
nodes=[];convmeta=[];weights={};t0=time.perf_counter()
for index,n in enumerate(model.graph.node):
    a=attrs(n)
    if n.op_type=='DequantizeLinear' and all(i in constants for i in n.input):
        constants[n.output[0]]=dq(*(constants[i] for i in n.input),axis=a.get('axis',1));continue
    record={'name':n.name,'op':n.op_type,'inputs':list(n.input),'outputs':list(n.output),'attrs':a,'original_index':index}
    if n.op_type=='Conv':
        w=constants[n.input[1]];co,ci,k,_=w.shape;group=a.get('group',1)
        spec={'id':len(convmeta),'name':n.name,'Cin':ci*group,'Cout':co,'K':k,'stride':a.get('strides',[1,1])[0],
              'padding':a.get('pads',[0,0,0,0])[0],'groups':group,'input':n.input[0],'output':n.output[0],
              'weight':n.input[1],'bias':n.input[2],'input_shape':shapes[n.input[0]]['shape'],
              'output_shape':shapes[n.output[0]]['shape']}
        wdq=producer.get(n.input[1]);xdq=producer.get(n.input[0]);bdq=producer.get(n.input[2])
        qout=next((c for c in consumers[n.output[0]] if c.op_type=='QuantizeLinear'),None)
        quant=bool(wdq and wdq.op_type=='DequantizeLinear' and xdq and xdq.op_type=='DequantizeLinear' and qout)
        spec['quantized']=quant;spec['FPGA_supported']=quant and group==1 and k in(1,3) and spec['stride'] in(1,2) and spec['Cin']<=512
        if quant:
            q={'input':xdq.input[0],'input_scale':xdq.input[1],'input_zp':xdq.input[2],
               'weight':wdq.input[0],'weight_scale':wdq.input[1],'weight_zp':wdq.input[2],
               'bias':bdq.input[0],'output':qout.output[0],'output_scale':qout.input[1],'output_zp':qout.input[2]}
            spec['quant']=q
            if spec['FPGA_supported']:
                qw=constants[q['weight']];wz=constants[q['weight_zp']].reshape(-1)
                assert np.all(wz==wz[0]);packed=[];blocks=[]
                for oc in range(0,co,32):
                    actualco=min(32,co-oc);cop=((actualco+7)//8)*8;parts=[]
                    for ic in range(0,spec['Cin'],32):
                        actualci=min(32,spec['Cin']-ic);cip=((actualci+7)//8)*8
                        padded=np.full((cop,cip,k,k),int(wz[0]),dtype=np.int8)
                        padded[:actualco,:actualci]=qw[oc:oc+actualco,ic:ic+actualci]
                        blocked=padded.reshape(cop//8,8,cip//8,8,k,k).transpose(0,2,4,5,1,3).copy().reshape(-1)
                        parts.append({'Cin_start':ic,'Cin_actual':actualci,'bytes':blocked.size,'offset':sum(x.size for x in packed)})
                        packed.append(blocked)
                    blocks.append({'Cout_start':oc,'Cout_actual':actualco,'chunks':parts})
                weights['conv%d'%spec['id']]=np.concatenate(packed)
                spec['packed_blocks']=blocks
        # Standalone FP32 Conv model works around full-graph OpenCV import failures.
        if not spec['FPGA_supported']:
            input_name='x';output_name='y'
            node=helper.make_node('Conv',[input_name,'w','b'],[output_name],**a)
            graph=helper.make_graph([node],n.name,
                [helper.make_tensor_value_info(input_name,TensorProto.FLOAT,spec['input_shape'])],
                [helper.make_tensor_value_info(output_name,TensorProto.FLOAT,spec['output_shape'])],
                [numpy_helper.from_array(w,'w'),numpy_helper.from_array(constants[n.input[2]],'b')])
            isolated=helper.make_model(graph,opset_imports=[helper.make_opsetid('',17)],ir_version=8)
            onnx.checker.check_model(isolated);onnx.save(isolated,O/('cpu_conv_%d.onnx'%spec['id']))
        record['conv_id']=spec['id'];convmeta.append(spec)
    nodes.append(record)
elapsed=(time.perf_counter()-t0)*1000
np.savez(O/'constants.npz',**constants);np.savez(O/'packed_weights.npz',**weights)
program={'model_source_sha256':hashlib.sha256(M.read_bytes()).hexdigest(),'model_source':str(M),
         'input':model.graph.input[0].name,'output':model.graph.output[0].name,'nodes':nodes,'convolutions':convmeta,
         'tensors':shapes,'offline_weight_and_graph_preparation_ms':elapsed}
(O/'graph.json').write_text(json.dumps(program,indent=2))
summary={'nodes':len(nodes),'convolutions':len(convmeta),'FPGA_convolutions':sum(s['FPGA_supported'] for s in convmeta),
         'quantized_CPU_grouped_conv':sum(s['quantized'] and not s['FPGA_supported'] for s in convmeta),
         'CPU_FP32_conv':sum(not s['quantized'] for s in convmeta),'max_Cin':max(s['Cin'] for s in convmeta),
         'max_Cout':max(s['Cout'] for s in convmeta),'offline_preparation_ms':elapsed,
         'packed_weight_bytes':sum(v.nbytes for v in weights.values()),
         'ops':dict(collections.Counter(n['op'] for n in nodes))}
(ROOT/'reports/stage_d'/('graph_preparation_'+args.output_name+'.json')).write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
