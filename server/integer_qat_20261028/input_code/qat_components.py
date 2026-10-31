"""Conv-boundary QAT reference. Non-Conv operations and biases remain FP32."""
from pathlib import Path
import copy, hashlib, json
import numpy as np
import torch
from torch import nn
from torch.ao.quantization import FakeQuantize, MinMaxObserver, PerChannelMinMaxObserver


class DivideRoundWeight(torch.autograd.Function):
    """ONNX-13 division then ties-to-even rounding; clipped straight-through gradient."""
    @staticmethod
    def forward(ctx, value, scale, zero):
        shape = [-1] + [1]*(value.ndim-1)
        s = scale.reshape(shape)
        z = zero.reshape(shape)
        quantised = torch.round(value/s) + z
        ctx.save_for_backward((quantised >= -128) & (quantised <= 127))
        return (torch.clamp(quantised,-128,127)-z)*s

    @staticmethod
    def backward(ctx, gradient):
        (mask,) = ctx.saved_tensors
        return gradient*mask, None, None

    @staticmethod
    def symbolic(g, value, scale, zero):
        # ONNX INT8 type id3. Scales remain per output channel on axis0.
        z = g.op('Cast',zero,to_i=3)
        q = g.op('QuantizeLinear',value,scale,z,axis_i=0)
        return g.op('DequantizeLinear',q,scale,z,axis_i=0)


class OnnxWeightFakeQuant(FakeQuantize):
    def forward(self, value):
        if self.observer_enabled[0] == 1:
            enabled = self.fake_quant_enabled.clone()
            self.disable_fake_quant()
            super().forward(value)
            self.fake_quant_enabled.copy_(enabled)
        if self.fake_quant_enabled[0] == 1:
            return DivideRoundWeight.apply(value,self.scale,self.zero_point)
        return value


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2), encoding='utf-8')


class QuantisedConvReference(nn.Module):
    def __init__(self, conv):
        super().__init__()
        self.conv = conv
        self.input_quant = FakeQuantize(observer=MinMaxObserver, quant_min=0, quant_max=255,
                                       dtype=torch.quint8, qscheme=torch.per_tensor_affine)
        self.output_quant = FakeQuantize(observer=MinMaxObserver, quant_min=0, quant_max=255,
                                        dtype=torch.quint8, qscheme=torch.per_tensor_affine)
        self.weight_quant = OnnxWeightFakeQuant(observer=PerChannelMinMaxObserver, quant_min=-128, quant_max=127,
                                        dtype=torch.qint8, qscheme=torch.per_channel_symmetric, ch_axis=0)

    def forward(self, x):
        x = self.input_quant(x)
        weight = self.weight_quant(self.conv.weight)
        value = torch.nn.functional.conv2d(x, weight, self.conv.bias, self.conv.stride,
                                           self.conv.padding, self.conv.dilation, self.conv.groups)
        return self.output_quant(value)


class Normalised(nn.Module):
    def __init__(self, encoder):
        super().__init__()
        self.encoder = encoder

    def forward(self, x):
        return torch.nn.functional.normalize(self.encoder(x), p=2, dim=1, eps=1e-12)


def make_encoder(checkpoint):
    from torchvision.models import mobilenet_v3_small
    model = mobilenet_v3_small(weights=None)
    encoder = nn.Sequential(model.features, model.avgpool, nn.Flatten()).eval()
    encoder.load_state_dict(torch.load(checkpoint, map_location='cpu', weights_only=True))
    return encoder


def fold_batchnorm(model):
    result = copy.deepcopy(model).eval()
    count = 0
    for module in list(result.modules()):
        if not isinstance(module, nn.Sequential):
            continue
        children = list(module._modules.items())
        for (conv_name, conv), (bn_name, bn) in zip(children, children[1:]):
            if isinstance(conv, nn.Conv2d) and isinstance(bn, nn.BatchNorm2d):
                module._modules[conv_name] = nn.utils.fuse_conv_bn_eval(conv, bn)
                module._modules[bn_name] = nn.Identity()
                count += 1
    assert not any(isinstance(m, nn.BatchNorm2d) for m in result.modules())
    return result, count


def insert_quantisers(model):
    result = copy.deepcopy(model)
    names = []
    def recurse(module, prefix=''):
        for name, child in list(module.named_children()):
            full = prefix + name
            if isinstance(child, nn.Conv2d):
                setattr(module, name, QuantisedConvReference(child))
                names.append(full)
            else:
                recurse(child, full + '.')
    recurse(result)
    assert len(names) == 52
    return result, names


def quant_mode(model, *, fake, observe):
    for module in model.modules():
        if isinstance(module, FakeQuantize):
            module.enable_fake_quant(fake)
            module.enable_observer(observe)


def qparam_digest(model):
    h = hashlib.sha256()
    for name, module in model.named_modules():
        if isinstance(module, FakeQuantize):
            h.update(name.encode())
            for value in [module.scale, module.zero_point, module.observer_enabled]:
                h.update(value.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def calibrate(model, tensors):
    quant_mode(model, fake=False, observe=True)
    model.eval()
    device = next(model.parameters()).device
    with torch.no_grad():
        for value in tensors:
            model(value.to(device))
    quant_mode(model, fake=True, observe=False)
    assert all(torch.isfinite(m.scale).all() and (m.scale > 0).all()
               for m in model.modules() if isinstance(m, FakeQuantize))


def ort_session(path, optimise=False):
    import onnxruntime as ort
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    options.graph_optimization_level = (ort.GraphOptimizationLevel.ORT_ENABLE_ALL if optimise
                                        else ort.GraphOptimizationLevel.ORT_DISABLE_ALL)
    return ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])


def export_graph(model, destination, example):
    cpu = copy.deepcopy(model).cpu().eval()
    quant_mode(cpu, fake=True, observe=False)
    torch.onnx.export(Normalised(cpu), example.cpu(), str(destination), input_names=['images'],
                      output_names=['embedding'], opset_version=13, do_constant_folding=True,
                      dynamo=False, dynamic_axes=None)
    if any(isinstance(m, FakeQuantize) for m in cpu.modules()):
        from onnx_canonical import canonicalise_activation_scalars
        raw_path = Path(destination).with_suffix('.torch_raw.onnx')
        assert not raw_path.exists()
        Path(destination).rename(raw_path)
        record = canonicalise_activation_scalars(raw_path, destination)
        save(Path(destination).with_suffix('.scalar_canonicalisation.json'), record)


def pack_constant_weights(source, destination, example):
    """Fold only constant weight QuantizeLinear; verify whole-model parity separately."""
    import onnx
    from onnx import helper, numpy_helper
    graph = onnx.load(source)
    producers = {name: node for node in graph.graph.node for name in node.output}
    arrays = {v.name: numpy_helper.to_array(v) for v in graph.graph.initializer}
    weight_nodes = []
    for conv in graph.graph.node:
        if conv.op_type != 'Conv':
            continue
        dequant = producers[conv.input[1]]
        assert dequant.op_type == 'DequantizeLinear'
        quant = producers[dequant.input[0]]
        assert quant.op_type == 'QuantizeLinear' and quant.input[0] in arrays
        assert arrays[quant.input[0]].dtype == np.float32
        weight_nodes.append(quant)
    assert len(weight_nodes) == 52 and len({n.output[0] for n in weight_nodes}) == 52
    # Evaluate the constant standard ONNX operation, including its exact rounding.
    probe = copy.deepcopy(graph)
    del probe.graph.output[:]
    probe.graph.output.extend([helper.make_tensor_value_info(n.output[0], onnx.TensorProto.INT8,
                             list(arrays[n.input[0]].shape)) for n in weight_nodes])
    import onnxruntime as ort
    options = ort.SessionOptions(); options.intra_op_num_threads = 2; options.inter_op_num_threads = 1
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    runtime = ort.InferenceSession(probe.SerializeToString(), sess_options=options, providers=['CPUExecutionProvider'])
    values = runtime.run(None, {'images': example.cpu().numpy()})
    remove = {n.output[0] for n in weight_nodes}
    retained = [n for n in graph.graph.node if not (n.op_type == 'QuantizeLinear' and n.output[0] in remove)]
    del graph.graph.node[:]; graph.graph.node.extend(retained)
    for node, value in zip(weight_nodes, values):
        assert value.dtype == np.int8
        graph.graph.initializer.append(numpy_helper.from_array(value, node.output[0]))
    # Remove orphaned constant nodes and original FP32 weight initializers.
    needed = {v.name for v in graph.graph.output}
    retained = []
    for node in reversed(graph.graph.node):
        if needed.intersection(node.output):
            retained.append(node); needed.update(node.input)
    del graph.graph.node[:]; graph.graph.node.extend(reversed(retained))
    initializers = [v for v in graph.graph.initializer if v.name in needed]
    del graph.graph.initializer[:]; graph.graph.initializer.extend(initializers)
    onnx.checker.check_model(graph, full_check=True)
    onnx.save(graph, destination)
    int_weights = {n.output[0]: v for n, v in zip(weight_nodes, values)}
    return {'packed_weight_tensors': len(values), 'packed_weight_bytes': sum(v.nbytes for v in values),
            'float_bias_and_non_conv_operations_retained': True,
            'source_bytes': Path(source).stat().st_size, 'packed_bytes': Path(destination).stat().st_size,
            'weight_bytes_sha256': hashlib.sha256(b''.join(v.tobytes() for v in int_weights.values())).hexdigest()}


def parity(model, unpacked, packed, tensors, directory):
    cpu = copy.deepcopy(model).cpu().eval()
    quant_mode(cpu, fake=True, observe=False)
    raw = ort_session(unpacked); reference = ort_session(packed); optimised = ort_session(packed, True)
    results = []; arrays = {'inputs': np.concatenate([x.cpu().numpy() for x in tensors])}
    torch_outputs = []; raw_outputs = []; packed_outputs = []; opt_outputs = []
    with torch.no_grad():
        for i, x in enumerate(tensors):
            x = x.cpu()
            a = torch.nn.functional.normalize(cpu(x), dim=1).numpy()
            b = raw.run(None, {'images': x.numpy()})[0]
            c = reference.run(None, {'images': x.numpy()})[0]
            d = optimised.run(None, {'images': x.numpy()})[0]
            err = float(np.max(np.abs(a-c)))
            cosine = float(np.sum(a.astype(float)*c.astype(float))/(np.linalg.norm(a)*np.linalg.norm(c)))
            packing_error = float(np.max(np.abs(b-c)))
            results.append({'training_vector': i, 'torch_packed_max_absolute_error': err,
                            'torch_packed_cosine': cosine, 'unpacked_packed_max_absolute_error': packing_error,
                            'default_optimisation_max_absolute_difference': float(np.max(np.abs(c-d))),
                            'reference_pass': err <= .001 and cosine >= .9999 and packing_error <= 1e-6})
            torch_outputs.append(a); raw_outputs.append(b); packed_outputs.append(c); opt_outputs.append(d)
    arrays.update(torch=np.concatenate(torch_outputs), unpacked=np.concatenate(raw_outputs),
                  packed=np.concatenate(packed_outputs), optimised=np.concatenate(opt_outputs))
    np.savez_compressed(Path(directory)/'export_parity_vectors.npz', **arrays)
    save(Path(directory)/'export_parity.json', results)
    return {'vectors': len(results), 'reference_all_pass': all(r['reference_pass'] for r in results),
            'default_optimisation_differences_retained': sum(r['default_optimisation_max_absolute_difference'] > 1e-6 for r in results),
            'max_reference_absolute_error': max(r['torch_packed_max_absolute_error'] for r in results),
            'max_packing_absolute_error': max(r['unpacked_packed_max_absolute_error'] for r in results)}
