import ctypes,pathlib
import numpy as np
def pointer(array):return ctypes.c_void_p(array.ctypes.data)
class NativeOps:
    def __init__(self,library):
        self.lib=ctypes.CDLL(str(library))
        p=ctypes.c_void_p;i=ctypes.c_int;f=ctypes.c_float
        signatures={'pack_tile':[p]+[i]*13+[p,p,p], 'unpack_i32':[p,p]+[i]*8,
                    'configure':[p,p],'wait_done':[p,p,p,p], 'quantize':[p,p,i,f,i],
                    'dequantize':[p,p,i,f,i],'accumulator_float':[p,p,i,i,p],
                    'lut_float':[p,p,i,p],'silu':[p,p,i],'matmul':[p,p,p,i,i,i]}
        # pack_tile dimensions: ci,h,w,co,oh,ow,oy,ox,k,stride,padding,zp =12.
        signatures['pack_tile']=[p]+[i]*12+[p,p,p]
        signatures['pack_tile_quant']=[p]+[i]*12+[p,p,p,p,p,p,i]
        signatures['pack_tile_cached']=[p]+[i]*12+[p,p,p,p,p,p,i,i]
        signatures['unpack_i8']=[p,p]+[i]*8
        signatures['configure_quant']=[p,p];signatures['wait_done_quant']=[p,p,p,p]
        signatures['configure_cache']=[p,p]
        signatures['configure_changed']=[p,p,p,p]
        signatures['set_neon_layout']=[i]
        signatures['lookup_int8']=[p,p,i,p]
        signatures['maxpool_float']=[p,p,p,i,i,i,i]
        signatures['set_parallel_elementwise']=[i]
        signatures['set_activation_prepack']=[i]
        signatures['submit_dma']=[p,p,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,i]
        for name,args in signatures.items():
            fn=getattr(self.lib,name);fn.argtypes=args;fn.restype=i if name in ('pack_tile','wait_done','pack_tile_quant','pack_tile_cached','wait_done_quant','submit_dma') else None
        self.luts={}
        self.pool_scratch={}
        self.pool_fallback_count=0
    def maxpool(self,x,k):
        x=np.ascontiguousarray(x,dtype=np.float32)
        n,c,h,w=x.shape
        # Installed NumPy's signed-zero tie choice depends on its SIMD path.
        # Preserve that implementation for exceptional values; ordinary finite
        # model activations use the faster separable kernel.
        if np.any(x.view(np.uint32)==0x80000000) or not np.all(np.isfinite(x)):
            self.pool_fallback_count+=1
            pad=k//2;source=np.pad(x,((0,0),(0,0),(pad,pad),(pad,pad)),constant_values=-np.inf)
            y=np.full_like(x,-np.inf)
            for yy in range(k):
                for xx in range(k):np.maximum(y,source[:,:,yy:yy+h,xx:xx+w],out=y)
            return y
        if x.shape not in self.pool_scratch:self.pool_scratch[x.shape]=np.empty_like(x)
        y=np.empty_like(x)
        self.lib.maxpool_float(pointer(x),pointer(y),pointer(self.pool_scratch[x.shape]),n*c,h,w,k)
        return y
    def quantize(self,x,s,z):
        x=np.ascontiguousarray(x,dtype=np.float32);y=np.empty(x.shape,dtype=np.int8)
        self.lib.quantize(pointer(x),pointer(y),x.size,float(s),int(z));return y
    def lookup_int8(self,x,table):
        x=np.ascontiguousarray(x,dtype=np.int8);table=np.ascontiguousarray(table,dtype=np.int8)
        y=np.empty(x.shape,dtype=np.int8)
        self.lib.lookup_int8(pointer(x),pointer(y),x.size,pointer(table));return y
    def dequantize(self,x,s,z):
        x=np.ascontiguousarray(x,dtype=np.int8);y=np.empty(x.shape,dtype=np.float32)
        self.lib.dequantize(pointer(x),pointer(y),x.size,float(s),int(z));return y
    def accumulator_float(self,x,s):
        x=np.ascontiguousarray(x,dtype=np.int32);s=np.ascontiguousarray(s,dtype=np.float32);y=np.empty(x.shape,dtype=np.float32)
        self.lib.accumulator_float(pointer(x),pointer(y),x.shape[-3],x.shape[-2]*x.shape[-1],pointer(s));return y
    def silu(self,x,q=None,scale=None,zp=None):
        y=np.empty(x.shape,dtype=np.float32)
        if q is not None:
            key=(float(scale),int(zp))
            if key not in self.luts:
                codes=np.arange(256,dtype=np.uint8).view(np.int8)
                real=(codes.astype(np.float32)-int(zp))*np.float32(scale)
                self.luts[key]=real*(np.float32(1)/(np.float32(1)+np.exp(-real)))
            q=np.ascontiguousarray(q);self.lib.lut_float(pointer(q),pointer(y),q.size,pointer(self.luts[key]))
        else:
            x=np.ascontiguousarray(x);self.lib.silu(pointer(x),pointer(y),x.size)
        return y
    def matmul(self,a,b):
        a=np.ascontiguousarray(a,dtype=np.float32);b=np.ascontiguousarray(b,dtype=np.float32)
        batch=np.broadcast_shapes(a.shape[:-2],b.shape[:-2]);m,k=a.shape[-2:];n=b.shape[-1]
        assert b.shape[-2]==k
        a=np.broadcast_to(a,batch+(m,k));b=np.broadcast_to(b,batch+(k,n))
        y=np.empty(batch+(m,n),dtype=np.float32)
        for index in np.ndindex(batch):self.lib.matmul(pointer(a[index]),pointer(b[index]),pointer(y[index]),m,n,k)
        return y
