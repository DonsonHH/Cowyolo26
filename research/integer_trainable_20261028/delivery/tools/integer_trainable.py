"""Exact bounded integer forward with an explicitly defined clipped STE.

DOUBLE convolution of integer operands is a numerical implementation, not a
claim of integer hardware execution. Non-Conv operations remain FP32.
"""
import copy, hashlib
import numpy as np
import torch
from torch import nn
from torch.autograd.function import once_differentiable
from torch.onnx.symbolic_helper import parse_args
import torch.nn.functional as F


def codes(x, w, sx, zx, sw):
    ix = torch.round(x / sx) + zx.to(torch.float32)
    iw = torch.round(w / sw.reshape(-1, 1, 1, 1))
    mask_x = (ix >= 0) & (ix <= 255)
    mask_w = (iw >= -128) & (iw <= 127)
    return torch.clamp(ix, 0, 255), torch.clamp(iw, -128, 127), mask_x, mask_w


class IntegerConvSTE(torch.autograd.Function):
    @staticmethod
    def forward(ctx, x, w, bias, sx, zx, sw, zw, sy, zy, stride, padding, dilation, groups):
        qx, qw, mask_x, mask_w = codes(x, w, sx, zx, sw)
        centered = qx - zx.to(torch.float32)
        # Bound includes absolute values of every product, independent of sum order.
        bound = w.shape[1] * w.shape[2] * w.shape[3] * float(centered.abs().max()) * float(qw.abs().max())
        assert bound <= np.iinfo(np.int32).max
        accumulator = F.conv2d(centered.double(), qw.double(), None, stride, padding, dilation, groups)
        assert torch.equal(accumulator, torch.round(accumulator))
        raw = accumulator * sx.double()
        raw = raw * sw.double().reshape(1, -1, 1, 1)
        raw = raw + bias.double().reshape(1, -1, 1, 1)
        raw = raw.float()
        iy = torch.round(raw / sy) + zy.to(torch.float32)
        mask_y = (iy >= 0) & (iy <= 255)
        output = (torch.clamp(iy, 0, 255) - zy.to(torch.float32)) * sy
        dequant_x = centered * sx
        dequant_w = qw * sw.reshape(-1, 1, 1, 1)
        ctx.save_for_backward(dequant_x, dequant_w, mask_x, mask_w, mask_y)
        ctx.parameters = stride, padding, dilation, groups
        ctx.input_shape, ctx.weight_shape = x.shape, w.shape
        return output

    @staticmethod
    @once_differentiable
    def backward(ctx, gradient):
        x, w, mx, mw, my = ctx.saved_tensors
        stride, padding, dilation, groups = ctx.parameters
        value_gradient = gradient * my
        dx = torch.nn.grad.conv2d_input(ctx.input_shape, w, value_gradient, stride, padding, dilation, groups) * mx if ctx.needs_input_grad[0] else None
        dw = torch.nn.grad.conv2d_weight(x, ctx.weight_shape, value_gradient, stride, padding, dilation, groups) * mw if ctx.needs_input_grad[1] else None
        db = value_gradient.sum((0, 2, 3)) if ctx.needs_input_grad[2] else None
        return dx, dw, db, None, None, None, None, None, None, None, None, None, None

    @staticmethod
    @parse_args('v', 'v', 'v', 'v', 'v', 'v', 'v', 'v', 'v', 'is', 'is', 'is', 'i')
    def symbolic(g, x, w, bias, sx, zx, sw, zw, sy, zy, stride, padding, dilation, groups):
        qx = g.op('QuantizeLinear', x, sx, zx)
        qw = g.op('QuantizeLinear', w, sw, zw, axis_i=0)
        shifted = g.op('Add', g.op('Cast', qw, to_i=5), g.op('Constant', value_t=torch.tensor(128, dtype=torch.int16)))
        encoded = g.op('Cast', shifted, to_i=2)
        wz = g.op('Constant', value_t=torch.tensor(128, dtype=torch.uint8))
        acc = g.op('ConvInteger', qx, encoded, zx, wz, strides_i=stride,
                   pads_i=list(padding) + list(padding), dilations_i=dilation, group_i=groups)
        shape = g.op('Constant', value_t=torch.tensor([1, -1, 1, 1], dtype=torch.int64))
        raw = g.op('Mul', g.op('Cast', acc, to_i=11), g.op('Cast', sx, to_i=11))
        raw = g.op('Mul', raw, g.op('Reshape', g.op('Cast', sw, to_i=11), shape))
        raw = g.op('Add', raw, g.op('Reshape', g.op('Cast', bias, to_i=11), shape))
        raw = g.op('Cast', raw, to_i=1)
        qy = g.op('QuantizeLinear', raw, sy, zy)
        return g.op('DequantizeLinear', qy, sy, zy)


class TrainableIntegerConv(nn.Module):
    def __init__(self, source):
        super().__init__()
        self.conv = copy.deepcopy(source.conv)
        for name, value in [
            ('sx', source.input_quant.scale.detach().reshape(())),
            ('zx', source.input_quant.zero_point.detach().to(torch.uint8).reshape(())),
            ('sw', source.weight_quant.scale.detach()),
            ('zw', source.weight_quant.zero_point.detach().to(torch.int8)),
            ('sy', source.output_quant.scale.detach().reshape(())),
            ('zy', source.output_quant.zero_point.detach().to(torch.uint8).reshape(()))]:
            self.register_buffer(name, value.clone())
        assert torch.all(self.zw == 0)

    def forward(self, x):
        return IntegerConvSTE.apply(x, self.conv.weight, self.conv.bias,
                                    self.sx, self.zx, self.sw, self.zw, self.sy, self.zy,
                                    self.conv.stride, self.conv.padding, self.conv.dilation, self.conv.groups)


def convert(source):
    from qat_components import QuantisedConvReference
    model = copy.deepcopy(source)
    names = []
    def visit(module, prefix=''):
        for name, child in list(module.named_children()):
            full = prefix + name
            if isinstance(child, QuantisedConvReference):
                setattr(module, name, TrainableIntegerConv(child))
                names.append(full)
            else:
                visit(child, full + '.')
    visit(model)
    assert len(names) == 52
    return model, names


def parameters_digest(model):
    h = hashlib.sha256()
    for name, value in model.named_buffers():
        h.update(name.encode())
        h.update(value.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def gradient_controls(device):
    torch.manual_seed(26)
    results = []
    for groups, channels, outputs in [(1, 2, 3), (3, 3, 3)]:
        x = (torch.randn(2, channels, 7, 8, device=device) * 5).requires_grad_(True)
        w = (torch.randn(outputs, channels // groups, 3, 3, device=device) * 1.2).requires_grad_(True)
        b = torch.randn(outputs, device=device, requires_grad=True)
        sx, zx, sy, zy = [torch.tensor(v, device=device, dtype=t) for v, t in [(.05, torch.float32), (128, torch.uint8), (.1, torch.float32), (128, torch.uint8)]]
        sw, zw = torch.full((outputs,), .01, device=device), torch.zeros(outputs, dtype=torch.int8, device=device)
        y = IntegerConvSTE.apply(x, w, b, sx, zx, sw, zw, sy, zy, (2, 1), (1, 1), (1, 1), groups)
        grad = torch.randn_like(y)
        a = torch.autograd.grad(y, [x, w, b], grad)
        qx, qw, mx, mw = codes(x.detach(), w.detach(), sx, zx, sw)
        dx, dw = (qx - zx.float()) * sx, qw * sw.reshape(-1, 1, 1, 1)
        xs = dx.detach().requires_grad_(True)
        ws = dw.detach().requires_grad_(True)
        bs = b.detach().requires_grad_(True)
        surrogate = F.conv2d(xs, ws, bs, (2, 1), (1, 1), (1, 1), groups)
        # Exactforward's output clipping mask; STE is a declared surrogate, not
        # the finite-difference derivative of the rounded forward function.
        exact_acc = F.conv2d((qx - zx.float()).double(), qw.double(), None, (2, 1), (1, 1), (1, 1), groups)
        raw = ((exact_acc * sx.double()) * sw.double().reshape(1, -1, 1, 1) + b.detach().double().reshape(1, -1, 1, 1)).float()
        iy = torch.round(raw / sy) + zy.float()
        my = (iy >= 0) & (iy <= 255)
        gx, gw, gb = torch.autograd.grad(surrogate * my, [xs, ws, bs], grad)
        reference = gx * mx, gw * mw, gb
        maximum = max(float((aa - bb).abs().max()) for aa, bb in zip(a, reference))
        assert maximum <= 1e-5
        assert all(torch.isfinite(v).all() for v in a)
        assert torch.count_nonzero(a[0][~mx]) == 0 and torch.count_nonzero(a[1][~mw]) == 0
        results.append({'device': str(device), 'groups': groups, 'maximum_STE_surrogate_gradient_difference': maximum,
                        'clipped_input_elements': int((~mx).sum()), 'clipped_weight_elements': int((~mw).sum()),
                        'clipped_output_elements': int((~my).sum()), 'finite_gradients': True})
    return results
