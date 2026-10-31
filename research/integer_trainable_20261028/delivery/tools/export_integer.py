from pathlib import Path
import copy
import numpy as np
import torch
import onnx
from onnx import helper, numpy_helper
from qat_components import Normalised
from integer_trainable import TrainableIntegerConv


def export(model, path, tensor):
    cpu = copy.deepcopy(model).cpu().eval()
    torch.onnx.export(Normalised(cpu), tensor.cpu(), str(path), input_names=['images'], output_names=['embedding'],
                      opset_version=13, do_constant_folding=True, dynamo=False)
    onnx.checker.check_model(onnx.load(path), full_check=True)


def pack(source, destination, model, tensor, make_runtime):
    graph = onnx.load(source)
    convs = [n for n in graph.graph.node if n.op_type == 'ConvInteger']
    shapes = [list(m.conv.weight.shape) for m in model.modules() if isinstance(m, TrainableIntegerConv)]
    assert len(convs) == len(shapes) == 52
    probe = copy.deepcopy(graph)
    del probe.graph.output[:]
    probe.graph.output.extend([helper.make_tensor_value_info(n.input[1], onnx.TensorProto.UINT8, s) for n, s in zip(convs, shapes)])
    runtime = make_runtime(probe.SerializeToString(), 'OFF')
    values = runtime.run(None, {'images': tensor.cpu().numpy()})
    constant_outputs = {n.input[1] for n in convs}
    assert len(constant_outputs) == 52 and sum(v.size for v in values) == 912008
    for conv, value in zip(convs, values):
        assert value.dtype == np.uint8
        graph.graph.initializer.append(numpy_helper.from_array(value, conv.input[1]))
    retained = [n for n in graph.graph.node if not set(n.output).intersection(constant_outputs)]
    del graph.graph.node[:]
    graph.graph.node.extend(retained)
    needed = {v.name for v in graph.graph.output}
    retained = []
    for node in reversed(graph.graph.node):
        if needed.intersection(node.output):
            retained.append(node)
            needed.update(node.input)
    del graph.graph.node[:]
    graph.graph.node.extend(reversed(retained))
    initializers = [v for v in graph.graph.initializer if v.name in needed]
    del graph.graph.initializer[:]
    graph.graph.initializer.extend(initializers)
    del graph.graph.value_info[:]
    onnx.checker.check_model(graph, full_check=True)
    onnx.save(graph, destination)
    return {'packed_weight_arrays': 52, 'packed_weight_bytes': sum(v.nbytes for v in values),
            'FP32_bias_and_non_conv_operations_retained': True,
            'DOUBLE_reconstruction_retained': True,
            'unpacked_bytes': Path(source).stat().st_size, 'packed_bytes': Path(destination).stat().st_size}
