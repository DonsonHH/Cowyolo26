"""Exact integer Conv, using explicit zero points and an INT64 proof accumulator."""
import numpy as np

def integer_conv(x, weights, bias, input_zero_point, weight_zero_point=0, stride=1, padding=0):
    x, weights, bias = np.asarray(x), np.asarray(weights), np.asarray(bias)
    if x.ndim == 4:
        if x.shape[0] != 1: raise ValueError('Batch 1 only')
        x = x[0]
    co, ci, kh, kw = weights.shape
    if x.shape[0] != ci or kh != kw or kh not in (1,3) or stride not in (1,2):
        raise ValueError('Unsupported Conv shape')
    zp = np.asarray(weight_zero_point, dtype=np.int64).reshape(-1)
    if zp.size == 1: zp = np.full(co, zp[0], dtype=np.int64)
    if zp.size != co: raise ValueError('Weight zero point must be scalar or per-output-channel')
    centered = x.astype(np.int64) - int(input_zero_point)
    centered = np.pad(centered, ((0,0),(padding,padding),(padding,padding)), constant_values=0)
    wc = weights.astype(np.int64) - zp[:,None,None,None]
    windows = np.lib.stride_tricks.sliding_window_view(centered,(kh,kw),axis=(1,2))[:,::stride,::stride]
    oh, ow = windows.shape[1:3]
    matrix = windows.transpose(0,3,4,1,2).reshape(ci*kh*kw,oh*ow)
    proof = wc.reshape(co,-1) @ matrix + bias.astype(np.int64).reshape(co,1)
    if np.any(proof < -(1<<31)) or np.any(proof > (1<<31)-1):
        raise OverflowError('INT32 Conv output overflow; no truncation allowed')
    return proof.astype(np.int32).reshape(co,oh,ow)

def accumulator_bound(weights, bias, input_zero_point, weight_zero_point):
    co = weights.shape[0]
    wz = np.broadcast_to(np.asarray(weight_zero_point,dtype=np.int64).reshape(-1),(co,))
    centered_weights = weights.astype(np.int64)-wz[:,None,None,None]
    largest_input = max(abs(-128-int(input_zero_point)),abs(127-int(input_zero_point)))
    bounds = largest_input*np.abs(centered_weights).reshape(co,-1).sum(1)+np.abs(bias.astype(np.int64))
    return {'per_channel_bound':bounds.tolist(),'maximum':int(bounds.max()),'int32_safe':bool(bounds.max()<(1<<31))}

def requantize_and_silu(acc, input_scale, weight_scale, output_scale, output_zero_point):
    """CPU fallback: FP32 dequantize -> actual Conv Q/DQ -> SiLU, ties-to-even."""
    scale=np.float32(input_scale)*np.asarray(weight_scale,dtype=np.float32)[:,None,None]
    real=acc.astype(np.float32)*scale
    q=np.clip(np.rint(real/np.float32(output_scale))+int(output_zero_point),-128,127).astype(np.int8)
    dq=(q.astype(np.float32)-int(output_zero_point))*np.float32(output_scale)
    silu=dq/(np.float32(1)+np.exp(-dq))
    return q,silu
