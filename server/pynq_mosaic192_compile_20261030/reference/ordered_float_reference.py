"""Explicit FP32 arithmetic order for non-convolution MatMul and Softmax.

No compiler/runtime code is called. expf is the host C99 scalar libm primitive,
used in the same way as the native program's std::exp(float), not NumPy SIMD exp.
"""
import ctypes,ctypes.util
import numpy as np
_libm=ctypes.CDLL(ctypes.util.find_library('m'))
_expf=_libm.expf;_expf.argtypes=[ctypes.c_float];_expf.restype=ctypes.c_float
def ordered_matmul(left,right):
    assert left.dtype==right.dtype==np.float32 and left.ndim>=2 and right.ndim>=2
    assert left.shape[-1]==right.shape[-2]
    batch=np.broadcast_shapes(left.shape[:-2],right.shape[:-2]);m,k=left.shape[-2:];n=right.shape[-1]
    a=np.broadcast_to(left,batch+(m,k));b=np.broadcast_to(right,batch+(k,n));out=np.zeros(batch+(m,n),np.float32)
    for i in range(k):
        product=np.multiply(a[...,:,i,None],b[...,None,i,:],dtype=np.float32)
        np.add(out,product,out=out)
    return out
def ordered_softmax(value,axis=-1):
    assert value.dtype==np.float32 and axis in [-1,value.ndim-1]
    flat=value.reshape(-1,value.shape[-1]);out=np.empty_like(flat)
    for row,target in zip(flat,out):
        maximum=np.max(row);total=np.float32(0)
        for i,v in enumerate(row):
            target[i]=np.float32(_expf(float(np.float32(v-maximum))))
            total=np.float32(total+target[i])
        np.divide(target,total,out=target)
    return out.reshape(value.shape)
def contract_toys():
    a=np.asarray([[[1,2,3],[4,5,6]]],np.float32);b=np.asarray([[1,2],[3,4],[5,6]],np.float32)
    assert np.array_equal(ordered_matmul(a,b),np.asarray([[[22,28],[49,64]]],np.float32))
    cancellation=ordered_matmul(np.asarray([[1e8,1,-1e8]],np.float32),np.ones((3,1),np.float32))
    assert cancellation[0,0]==0,'FP32orderedcontractmustnotbequietlyreplacedwithFP64sum'
    assert np.array_equal(ordered_softmax(np.zeros((2,4),np.float32)),np.full((2,4),.25,np.float32))
    return {'FP32_ordered_MatMul_exact_integer_toy':True,'FP32_cancellation_not_FP64':True,'Softmax_equal_logits_exact':True}
