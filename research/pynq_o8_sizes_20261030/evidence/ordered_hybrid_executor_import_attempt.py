"""One explicit ONNX scheduler with interchangeable integer Conv dispatch."""
import pathlib,json,time,collections
import numpy as np
from ordered_float_reference import ordered_matmul,ordered_softmax,cv2

def dequantize(x,scale,zp,axis=1):
    if scale.size>1:
        shape=[1]*x.ndim;shape[axis]=scale.size;scale=scale.reshape(shape);zp=zp.reshape(shape)
    return (x.astype(np.float32)-zp.astype(np.float32))*scale

class YOLOHybridExecutor:
    def __init__(self,model_dir,conv_backend=None,native=None,quantization_mode='float32',fuse_activation=False,group_cpu_heads=True):
        self.root=pathlib.Path(model_dir)
        self.graph=json.loads((self.root/'graph.json').read_text())
        with np.load(self.root/'constants.npz') as archive:self.constants={k:archive[k] for k in archive.files}
        self.conv_backend=conv_backend;self.native=native;self.nets={};self.profile=[]
        self.specs={s['id']:s for s in self.graph['convolutions']}
        self.activation_fusion={};self.activation_tables={}
        if (self.root/'activation_tables.npz').exists():
            with np.load(self.root/'activation_tables.npz') as archive:self.activation_tables={k:archive[k] for k in archive.files}
            if native:
                for spec in self.specs.values():
                    if spec['quantized']:
                        q=spec['quant'];key=(float(self.constants[q['output_scale']]),int(self.constants[q['output_zp']]))
                        native.luts[key]=self.activation_tables['silu%d'%spec['id']]
        if fuse_activation:
            self.activation_fusion={int(k):v for k,v in json.loads((self.root/'activation_fusion.json').read_text()).items()}
            if conv_backend is not None and hasattr(conv_backend,'fusion'):
                conv_backend.fusion=self.activation_fusion
        self.quantization_mode=quantization_mode;self.fixed_parameters={}
        if quantization_mode=='fixed':
            from fixed_point import coefficients
            remove=set();remove_names=set();replacement={}
            for spec in self.specs.values():
                if (spec['FPGA_supported'] or spec.get('CPU_INT8_supported',False)):
                    q=spec['quant'];ratio=float(self.constants[q['input_scale']])*self.constants[q['weight_scale']].astype(np.float64)/float(self.constants[q['output_scale']])
                    self.fixed_parameters[spec['id']]=coefficients(ratio)
                    remove.add(q['output'])
                    output=q['output']
                    if spec['id'] in self.activation_fusion:
                        details=self.activation_fusion[spec['id']];output=details['output'];remove_names.update(details['remove_nodes'])
                    replacement[spec['id']]=dict(name=spec['name'],op='QuantConv',inputs=[q['input'],q['weight'],q['bias']],
                        outputs=[output],attrs={},conv_id=spec['id'])
            compiled=[]
            for node in self.graph['nodes']:
                if node['name'] in remove_names:continue
                if node['op']=='QuantizeLinear' and node['outputs'][0] in remove:continue
                if node['op']=='Conv' and node['conv_id'] in replacement:compiled.append(replacement[node['conv_id']])
                else:compiled.append(node)
            used={name for n in compiled for name in n['inputs']}
            self.graph['nodes']=[n for n in compiled if n['op']!='DequantizeLinear' or n['outputs'][0] in used]
        # Fuse the exact Sigmoid+Mul expression into one CPU kernel/LUT dispatch.
        producers={o:n for n in self.graph['nodes'] for o in n['outputs']};fused=[];skip=set()
        for n in self.graph['nodes']:
            if n['op']=='Mul':
                sig=next((producers.get(i) for i in n['inputs'] if producers.get(i,{}).get('op')=='Sigmoid'),None)
                if sig and sig['inputs'][0] in n['inputs']:
                    nn=dict(n);nn['op']='SiLU';nn['inputs']=[sig['inputs'][0]];fused.append(nn);skip.add(sig['name']);continue
            fused.append(n)
        self.graph['nodes']=[n for n in fused if n['name'] not in skip]
        self.producers={o:n for n in self.graph['nodes'] for o in n['outputs']}
        self.head_nets={};self.grouped_head_ids=set()
        if group_cpu_heads and (self.root/'cpu_heads.json').exists():
            for head in json.loads((self.root/'cpu_heads.json').read_text()):
                selected=set(head['nodes']);first=next(i for i,n in enumerate(self.graph['nodes']) if n['name'] in selected)
                replacement={'name':'CPU_head_%d'%head['scale'],'op':'CPUHead','inputs':[head['input']],
                             'outputs':head['outputs'],'attrs':head,'original_index':first}
                current=self.graph['nodes'];self.graph['nodes']=[replacement if i==first else n for i,n in enumerate(current) if i==first or n['name'] not in selected]
                self.grouped_head_ids.update(s['id'] for s in self.specs.values() if s['name'] in selected)
                self.head_nets[head['scale']]=cv2.dnn.readNetFromONNX(str(self.root/('cpu_head_%d.onnx'%head['scale'])))
        # Keep CPU nets and model constants across frames.
        for spec in self.specs.values():
            if not (spec['FPGA_supported'] or spec.get('CPU_INT8_supported',False)) and spec['id'] not in self.grouped_head_ids:
                net=cv2.dnn.readNetFromONNX(str(self.root/('cpu_conv_%d.onnx'%spec['id'])))
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.nets[spec['id']]=net
        self.required_inputs={n['name']:list(n['inputs']) for n in self.graph['nodes']}
        for n in self.graph['nodes']:
            if n['op']=='Conv' and self.specs[n['conv_id']]['FPGA_supported']:
                self.required_inputs[n['name']].append(self.specs[n['conv_id']]['quant']['input'])
            if n['op']=='SiLU':
                dq=self.producers.get(n['inputs'][0])
                if dq and dq['op']=='DequantizeLinear':self.required_inputs[n['name']].append(dq['inputs'][0])
        self.use_counts=collections.Counter(i for values in self.required_inputs.values() for i in values if i)
        self.quant_conv_by_output={s['output']:s for s in self.specs.values() if (s['FPGA_supported'] or s.get('CPU_INT8_supported',False))}
        from head_lut import optimize
        optimize(self)

    def run(self,image_tensor,boundary_callback=None,progress=False):
        tensors=dict(self.constants);tensors[self.graph['input']]=np.ascontiguousarray(image_tensor,dtype=np.float32)
        counts=self.use_counts.copy();self.profile=[];start=time.perf_counter()
        if self.conv_backend is not None and hasattr(self.conv_backend,'profile'):self.conv_backend.profile=[]
        for node in self.graph['nodes']:
            inputs=[tensors[i] if i else None for i in node['inputs']]
            a=node['attrs'];op=node['op'];t0=time.perf_counter()
            if op in ('Conv','QuantConv'):
                spec=self.specs[node['conv_id']]
                if (spec['FPGA_supported'] or spec.get('CPU_INT8_supported',False)):
                    q=spec['quant'];x=tensors[q['input']];w=self.constants[q['weight']];b=self.constants[q['bias']]
                    if self.conv_backend is None:
                        from integer_conv_reference import integer_conv
                        acc=integer_conv(x,w,b,int(self.constants[q['input_zp']]),self.constants[q['weight_zp']],spec['stride'],spec['padding'])
                    else:acc=self.conv_backend.execute(x,w,b,spec,self.constants)
                    if op=='QuantConv':
                        if getattr(self.conv_backend,'output_kind','int32')=='int8':y=acc
                        else:
                            from fixed_point import requantize
                            m,s=self.fixed_parameters[spec['id']];y=requantize(acc,m,s,int(self.constants[q['output_zp']]))
                            if spec['id'] in self.activation_fusion:y=self.activation_tables['activation%d'%spec['id']][y.view(np.uint8)]
                    else:
                        scale=np.float32(self.constants[q['input_scale']])*self.constants[q['weight_scale']][:,None,None]
                        y=self.native.accumulator_float(acc,scale) if self.native else acc.astype(np.float32)*scale
                    if y.ndim==3:y=y[None]
                else:
                    self.nets[spec['id']].setInput(np.ascontiguousarray(inputs[0],dtype=np.float32));y=self.nets[spec['id']].forward()
            elif op=='CPUHead':
                net=self.head_nets[a['scale']];net.setInput(np.ascontiguousarray(inputs[0],dtype=np.float32));y=net.forward(a['names'])
            elif op=='FloatLookup':
                codes,table=inputs
                if self.native:
                    from native_ops import pointer
                    y=np.empty(codes.shape,np.float32);self.native.lib.lut_float(pointer(np.ascontiguousarray(codes)),pointer(y),codes.size,pointer(table))
                else:y=table[codes.view(np.uint8)]
            elif op=='Identity':y=inputs[0]
            elif op=='Int8Lookup':y=inputs[1][inputs[0].view(np.uint8)]
            elif op=='QuantizeLinear':
                x,s,z=inputs;axis=a.get('axis',1)
                if s.size>1:
                    shape=[1]*x.ndim;shape[axis]=s.size;s=s.reshape(shape);z=z.reshape(shape)
                if self.native and s.size==1 and z.dtype==np.int8:y=self.native.quantize(x,s,z)
                else:
                    limits=np.iinfo(z.dtype);y=np.clip(np.rint(x/s)+z,limits.min,limits.max).astype(z.dtype)
            elif op=='DequantizeLinear':
                y=self.native.dequantize(*inputs) if self.native and inputs[1].size==1 and inputs[0].dtype==np.int8 else dequantize(*inputs,axis=a.get('axis',1))
            elif op=='SiLU':
                dq=self.producers.get(node['inputs'][0]);q=None
                if dq and dq['op']=='DequantizeLinear':q=tensors[dq['inputs'][0]]
                if self.native:y=self.native.silu(inputs[0],q,self.constants[dq['inputs'][1]] if q is not None else None,self.constants[dq['inputs'][2]] if q is not None else None)
                else:
                    if q is not None:
                        spec=next(s for s in self.specs.values() if s['quantized'] and s['quant']['output']==dq['inputs'][0])
                        if self.activation_tables:y=self.activation_tables['silu%d'%spec['id']][q.view(np.uint8)]
                        else:
                            x=inputs[0];sig=np.empty_like(x);pos=x>=0;sig[pos]=1/(1+np.exp(-x[pos]));e=np.exp(x[~pos]);sig[~pos]=e/(1+e);y=x*sig
                    else:
                        x=inputs[0];sig=np.empty_like(x);pos=x>=0;sig[pos]=1/(1+np.exp(-x[pos]));e=np.exp(x[~pos]);sig[~pos]=e/(1+e);y=x*sig
            elif op=='Sigmoid':
                x=inputs[0];y=np.float32(1)/(np.float32(1)+np.exp(-np.maximum(x,np.float32(-80))))
                extreme=x<-80
                if np.any(extreme):
                    e=np.exp(x[extreme]);y[extreme]=e/(np.float32(1)+e)
            elif op in ('Add','Sub','Mul','Div','Mod'):
                functions={'Add':np.add,'Sub':np.subtract,'Mul':np.multiply,'Div':np.divide,'Mod':np.mod}
                f=functions[op]
                if op=='Div' and np.issubdtype(inputs[0].dtype,np.integer):f=np.floor_divide
                y=f(*inputs)
            elif op=='Concat':y=np.concatenate(inputs,axis=a['axis'])
            elif op=='Split':
                axis=a.get('axis',0);sizes=inputs[1] if len(inputs)>1 else a.get('split')
                y=np.split(inputs[0],np.cumsum(sizes)[:-1],axis=axis) if sizes is not None else np.split(inputs[0],len(node['outputs']),axis=axis)
            elif op=='Reshape':
                shape=inputs[1].astype(np.int64).copy()
                if not a.get('allowzero',0):
                    for j in range(len(shape)):
                        if shape[j]==0:shape[j]=inputs[0].shape[j]
                y=inputs[0].reshape(tuple(shape))
            elif op=='Transpose':y=np.transpose(inputs[0],a.get('perm'))
            elif op=='MatMul':
                if self.native is not None:y=self.native.matmul(inputs[0],inputs[1])
                else:y=ordered_matmul(*inputs)
            elif op=='Softmax':
                y=ordered_softmax(inputs[0],a.get('axis',-1))
            elif op=='MaxPool':
                x=inputs[0];kh,kw=a['kernel_shape'];pads=a.get('pads',[0,0,0,0]);s0,s1=a.get('strides',[1,1])
                padded=np.pad(x,((0,0),(0,0),(pads[0],pads[2]),(pads[1],pads[3])),constant_values=-np.inf)
                oh=(padded.shape[2]-kh)//s0+1;ow=(padded.shape[3]-kw)//s1+1
                y=np.full((x.shape[0],x.shape[1],oh,ow),-np.inf,dtype=x.dtype)
                for yy in range(kh):
                    for xx in range(kw):np.maximum(y,padded[:,:,yy:yy+oh*s0:s0,xx:xx+ow*s1:s1],out=y)
            elif op=='Resize':
                assert a['mode']=='nearest' and a['coordinate_transformation_mode']=='asymmetric' and a['nearest_mode']=='floor'
                x=inputs[0];scales=inputs[2];oh=int(x.shape[2]*scales[2]);ow=int(x.shape[3]*scales[3])
                y=x[:,:,np.minimum(np.floor(np.arange(oh)/scales[2]).astype(int),x.shape[2]-1)[:,None],
                           np.minimum(np.floor(np.arange(ow)/scales[3]).astype(int),x.shape[3]-1)[None,:]]
            elif op=='Slice':
                x=inputs[0];starts,ends=inputs[1:3];axes=inputs[3] if len(inputs)>3 else np.arange(len(starts));steps=inputs[4] if len(inputs)>4 else np.ones(len(starts),dtype=int)
                slices=[slice(None)]*x.ndim
                for s,e,axis,step in zip(starts,ends,axes,steps):slices[int(axis)]=slice(int(s),int(e),int(step))
                y=x[tuple(slices)]
            elif op=='ReduceMax':y=inputs[0].max(axis=tuple(a.get('axes',range(inputs[0].ndim))),keepdims=bool(a.get('keepdims',1)))
            elif op=='TopK':
                from fast_topk import select
                y=select(inputs[0],int(inputs[1].reshape(-1)[0]),a.get('axis',-1),a.get('largest',1))
            elif op=='Unsqueeze':
                y=inputs[0]
                for axis in sorted(int(v) for v in (inputs[1] if len(inputs)>1 else a['axes'])):y=np.expand_dims(y,axis)
            elif op=='Expand':y=np.broadcast_to(inputs[0],np.broadcast_shapes(inputs[0].shape,tuple(inputs[1])))
            elif op=='GatherElements':y=np.take_along_axis(inputs[0],inputs[1].astype(np.int64),axis=a.get('axis',0))
            elif op=='Flatten':
                x=inputs[0];axis=a.get('axis',1);y=x.reshape(int(np.prod(x.shape[:axis])),int(np.prod(x.shape[axis:])))
            elif op=='Cast':y=inputs[0].astype({1:np.float32,2:np.uint8,3:np.int8,6:np.int32,7:np.int64,9:np.bool_}[a['to']])
            else:raise NotImplementedError(op)
            outputs=y if isinstance(y,(list,tuple)) else [y]
            for name,value in zip(node['outputs'],outputs):
                tensors[name]=value
                if boundary_callback is not None:boundary_callback(name,value,node)
            self.profile.append({'name':node['name'],'op':op,'ms':(time.perf_counter()-t0)*1000})
            if progress and op in ('Conv','QuantConv'):print('CONV_DONE',node['conv_id'],node['name'],self.profile[-1]['ms'],flush=True)
            for name in self.required_inputs[node['name']]:
                if name:
                    counts[name]-=1
                    if counts[name]==0 and name not in self.constants and name!=self.graph['output']:tensors.pop(name,None)
        output=tensors[self.graph['output']].copy()
        self.elapsed_ms=(time.perf_counter()-start)*1000
        return output
