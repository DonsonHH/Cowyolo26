"""ONNX structure and static allocation sketch; never an FPGA resource report."""
from collections import Counter
from pathlib import Path
import math
import numpy as np
import onnx
from onnx import numpy_helper

def audit_graph(path):
    model=onnx.load(path);onnx.checker.check_model(model,full_check=True)
    inferred=onnx.shape_inference.infer_shapes(model,strict_mode=True,data_prop=True)
    arrays={t.name:numpy_helper.to_array(t) for t in model.graph.initializer}
    shapes={name:list(array.shape) for name,array in arrays.items()}
    sizes={name:int(array.nbytes) for name,array in arrays.items()}
    dtypes={name:str(array.dtype) for name,array in arrays.items()}
    def info(value):
        kind=value.type.tensor_type
        dims=[int(d.dim_value) if d.HasField('dim_value') else None for d in kind.shape.dim]
        try:width=np.dtype(onnx.helper.tensor_dtype_to_np_dtype(kind.elem_type)).itemsize
        except Exception:width=None
        return dims,math.prod(dims)*width if width is not None and all(v is not None for v in dims) else None
    for value in list(inferred.graph.input)+list(inferred.graph.value_info)+list(inferred.graph.output):
        dims,size=info(value);shapes[value.name]=dims;sizes[value.name]=size
    operations=Counter(node.op_type for node in model.graph.node)
    constants=set(arrays)
    for node in model.graph.node:
        if node.op_type=='Constant':constants.update(node.output)
    consumers={}
    for index,node in enumerate(model.graph.node):
        for name in node.input:consumers[name]=index
    for value in model.graph.output:consumers[value.name]=len(model.graph.node)
    live={v.name:sizes.get(v.name) for v in model.graph.input if v.name not in constants}
    largest=max((n for name,n in sizes.items() if name not in constants and n is not None),default=0)
    peak=sum(n for n in live.values() if n is not None);unknown=set();macs=0;convs=[]
    for index,node in enumerate(model.graph.node):
        for name in node.output:
            if name not in constants:
                live[name]=sizes.get(name)
                if live[name] is None:unknown.add(name)
        peak=max(peak,sum(n for n in live.values() if n is not None))
        if node.op_type=='Conv':
            weight=arrays.get(node.input[1]);shape=shapes.get(node.output[0])
            # Quantized graphs feed dequantized weights; report MACs only when
            # the directly referenced initializer shape is explicit.
            if weight is not None and shape and all(x is not None for x in shape):
                value=math.prod(shape)*math.prod(weight.shape[1:]);macs+=value
                convs.append({'name':node.name,'weight_shape':list(weight.shape),'output_shape':shape,'MACs':value,
                              'group':next((int(a.i) for a in node.attribute if a.name=='group'),1)})
        for name in list(live):
            if consumers.get(name,-1)<=index:live.pop(name)
    bytype=Counter()
    for array in arrays.values():bytype[str(array.dtype)]+=int(array.nbytes)
    return {'file':str(path),'file_bytes':Path(path).stat().st_size,'IR_version':model.ir_version,
            'opset':{o.domain or 'ai.onnx':o.version for o in model.opset_import},
            'checker_full_check':'PASS','nodes':len(model.graph.node),'operator_counts':dict(operations),
            'initializers':len(arrays),'initializer_bytes':sum(int(a.nbytes) for a in arrays.values()),
            'initializer_bytes_by_dtype':dict(bytype),'largest_inferred_nonconstant_tensor_bytes':largest,
            'static_live_known_tensor_peak_bytes_sketch':peak,'unknown_output_size_tensors':sorted(unknown),
            'static_liveness_scope':'Sequential allocation sketch of known graph tensors; assumes no aliasing/reuse, excludes parameters, kernel workspaces, planner alignment, runtime/decoder/DMA buffers. Unknown shapes make the peak incomplete; it is not an upper bound or hardware BRAM utilisation.',
            'Conv_MACs_direct_initializer_only':macs,'Conv_details':convs,
            'inputs':[{'name':v.name,'shape':shapes.get(v.name)} for v in model.graph.input],
            'outputs':[{'name':v.name,'shape':shapes.get(v.name)} for v in model.graph.output],
            'integer_quantised_initializers':sum(np.issubdtype(a.dtype,np.integer) and a.dtype.itemsize==1 for a in arrays.values()),
            'is_fpga_compile_proof':False}
