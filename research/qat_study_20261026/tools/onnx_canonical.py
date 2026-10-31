"""Represent per-tensor activation scale/zero point as ONNX scalar constants."""
from pathlib import Path
import onnx
from onnx import numpy_helper


def canonicalise_activation_scalars(source, destination):
    model = onnx.load(source)
    arrays = {v.name:numpy_helper.to_array(v) for v in model.graph.initializer}
    producers = {s:n for n in model.graph.node for s in n.output}
    targets = set()
    for node in model.graph.node:
        if node.op_type not in ['QuantizeLinear','DequantizeLinear']:
            continue
        if '/input_quant/' not in node.name and '/output_quant/' not in node.name:
            continue
        for name in node.input[1:3]:
            while name not in arrays:
                producer = producers[name]
                assert producer.op_type == 'Identity', (name, producer.op_type)
                name = producer.input[0]
            assert arrays[name].size == 1
            targets.add(name)
    changed = []
    for i, value in enumerate(list(model.graph.initializer)):
        if value.name in targets and arrays[value.name].shape != ():
            assert arrays[value.name].shape == (1,)
            model.graph.initializer[i].CopyFrom(numpy_helper.from_array(arrays[value.name].reshape(()), value.name))
            changed.append(value.name)
    onnx.checker.check_model(model, full_check=True)
    onnx.save(model, destination)
    return {'changed_initializer_shapes_only':len(changed), 'names':sorted(changed),
            'values_unchanged':True, 'reference':'ONNX QuantizeLinear-13 per-tensor scale and zero-point are scalars'}
