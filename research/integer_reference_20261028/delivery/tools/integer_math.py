"""Explicit numerical reference; deliberately uses exact INT64 dot products."""
import numpy as np


def digest(array):
    import hashlib
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def quantise_u8(value, scale, zero):
    value = np.asarray(value, dtype=np.float32)
    scale = np.asarray(scale, dtype=np.float32).reshape(())
    zero = int(np.asarray(zero).reshape(()))
    return np.clip(np.rint(value / scale) + zero, 0, 255).astype(np.uint8)


def convolution(qx, qw, zx, zw, strides, pads, dilations, group):
    assert qx.dtype == qw.dtype == np.uint8
    x = qx.astype(np.int64) - int(zx)
    w = qw.astype(np.int64) - int(zw)
    n, c, h, width = x.shape
    m, cg, kh, kw = w.shape
    assert c == cg * group and m % group == 0
    sy, sx = strides
    dy, dx = dilations
    top, left, bottom, right = pads
    bound = cg * kh * kw * int(np.max(np.abs(x))) * int(np.max(np.abs(w)))
    assert bound <= np.iinfo(np.int32).max
    padded = np.pad(x, ((0, 0), (0, 0), (top, bottom), (left, right)))
    windows = np.lib.stride_tricks.sliding_window_view(
        padded, ((kh - 1) * dy + 1, (kw - 1) * dx + 1), axis=(2, 3))
    windows = windows[:, :, ::sy, ::sx, ::dy, ::dx]
    oh, ow = windows.shape[2:4]
    result = np.empty((n, m, oh, ow), dtype=np.int64)
    mg = m // group
    for g in range(group):
        patch = windows[:, g * cg:(g + 1) * cg]
        patch = patch.transpose(0, 2, 3, 1, 4, 5).reshape(n, oh * ow, -1)
        weight = w[g * mg:(g + 1) * mg].reshape(mg, -1)
        values = patch @ weight.T
        result[:, g * mg:(g + 1) * mg] = values.transpose(0, 2, 1).reshape(n, mg, oh, ow)
    assert int(np.max(np.abs(result))) <= bound
    return result, bound


def reconstruct(accumulator, input_scale, weight_scale, bias):
    value = accumulator.astype(np.float64) * np.asarray(input_scale, dtype=np.float64).reshape(())
    value = value * np.asarray(weight_scale, dtype=np.float64).reshape(1, -1, 1, 1)
    value = value + np.asarray(bias, dtype=np.float64).reshape(1, -1, 1, 1)
    return value.astype(np.float32)


def controls():
    """Scalar convolution oracle including group, padding, stride and dilation."""
    rng = np.random.default_rng(26)
    records = []
    cases = [((1, 2, 5, 6), (3, 2, 3, 3), [1, 1], [1, 1, 1, 1], [1, 1], 1),
             ((1, 4, 7, 8), (4, 1, 3, 3), [2, 2], [1, 0, 1, 0], [1, 1], 4),
             ((1, 4, 7, 8), (6, 2, 2, 2), [1, 2], [1, 2, 0, 1], [2, 2], 2)]
    for xshape, wshape, strides, pads, dilations, group in cases:
        x = rng.integers(0, 256, xshape, dtype=np.uint8)
        w = rng.integers(0, 256, wshape, dtype=np.uint8)
        result, bound = convolution(x, w, 143, 128, strides, pads, dilations, group)
        scalar = np.zeros_like(result)
        cg = xshape[1] // group
        mg = wshape[0] // group
        for index in np.ndindex(*result.shape):
            ni, mi, yi, xi = index
            value = 0
            for ci in range(cg):
                channel = (mi // mg) * cg + ci
                for ky in range(wshape[2]):
                    for kx in range(wshape[3]):
                        y = yi * strides[0] + ky * dilations[0] - pads[0]
                        xx = xi * strides[1] + kx * dilations[1] - pads[1]
                        if 0 <= y < xshape[2] and 0 <= xx < xshape[3]:
                            value += (int(x[ni, channel, y, xx]) - 143) * (int(w[mi, ci, ky, kx]) - 128)
            scalar[index] = value
        assert np.array_equal(result, scalar)
        records.append({'input': xshape, 'weight': wshape, 'group': group,
                        'output_elements': result.size, 'maximum_scalar_difference': 0,
                        'INT32_absolute_sum_bound': bound})
    ties = np.array([-.5, .5, 1.5, 2.5, 254.5, 255.5], dtype=np.float32)
    assert np.array_equal(quantise_u8(ties, 1., 0), [0, 0, 2, 2, 254, 255])
    return records
