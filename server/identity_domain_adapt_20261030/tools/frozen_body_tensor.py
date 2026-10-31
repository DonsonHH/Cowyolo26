"""Torch-free NCNN body encoder and the frozen Pillow body transform."""
from pathlib import Path
import ctypes
import numpy as np
from PIL import Image,ImageOps

def body_tensor(image):
    # Match the frozen Pillow11.3 training transform geometry on Pillow9.0.1.
    # Pillow9 ImageOps.contain/pad truncate; Pillow11 rounds both resize and offset.
    image=image.convert('RGB');size=(224,224)
    ratio=image.width/image.height
    target=(224,round(image.height/image.width*224)) if ratio>1 else (round(image.width/image.height*224),224) if ratio<1 else size
    resized=image.resize(target,resample=getattr(Image,'Resampling',Image).BILINEAR)
    if resized.size==size:image=resized
    else:
        image=Image.new('RGB',size,(127,127,127))
        position=(round((224-resized.width)*.5),0) if resized.width!=224 else (0,round((224-resized.height)*.5))
        image.paste(resized,position)
    x=np.ascontiguousarray(np.asarray(image,dtype=np.uint8).transpose(2,0,1),dtype=np.float32)/np.float32(255)
    x-=np.asarray([.485,.456,.406],np.float32)[:,None,None]
    x/=np.asarray([.229,.224,.225],np.float32)[:,None,None]
    return np.ascontiguousarray(x[None])

class Encoder:
    def __init__(self,root,threads=1):
        root=Path(root);self.lib=ctypes.CDLL(str(root/'libcow_encoder_v2.so'))
        ptr=ctypes.c_void_p
        self.lib.cow_ncnn_create.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];self.lib.cow_ncnn_create.restype=ptr
        self.lib.cow_ncnn_run.argtypes=[ptr,ptr,ptr];self.lib.cow_ncnn_run.restype=ctypes.c_int
        self.lib.cow_ncnn_error.restype=ctypes.c_char_p;self.lib.cow_ncnn_destroy.argtypes=[ptr]
        self.handle=self.lib.cow_ncnn_create(str(root/'encoder.ncnn.param').encode(),str(root/'encoder.ncnn.bin').encode(),threads)
        if not self.handle:raise RuntimeError(self.lib.cow_ncnn_error().decode())
    def run(self,x):
        x=np.ascontiguousarray(x,dtype=np.float32);assert x.shape==(1,3,224,224)
        output=np.empty(576,np.float32)
        code=self.lib.cow_ncnn_run(self.handle,x.ctypes.data,output.ctypes.data)
        if code:raise RuntimeError(code,self.lib.cow_ncnn_error().decode())
        assert np.isfinite(output).all()
        return output
    def close(self):
        if self.handle:self.lib.cow_ncnn_destroy(self.handle);self.handle=None
