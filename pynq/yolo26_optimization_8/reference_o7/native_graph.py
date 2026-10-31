"""One native call/frame; PC uses an independent exact integer Conv callback only."""
import os,sys,pathlib,ctypes,json,time
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parent
P=ctypes.c_void_p;CB=ctypes.CFUNCTYPE(ctypes.c_int,ctypes.c_int,P,P)
class NativeGraph:
 def __init__(self,size=192,pc=False,library=None,program=None,model_dir=None):
  self.size=size;self.pc=pc;self.program=ROOT/(program or f'program_r{size}');self.meta=json.loads((self.program/'program.json').read_text());self.device=None;self.callback=None;self.failure=None
  # Check actual core0x60004 banking limits before opening CMA/submitting DMA.
  # A Co32 K3 tile uses TWO output-pair regions per 512-word weight bank.
  for node in self.meta['nodes']:
   if node['op']=='QuantConv':
    sid,ci,co,k,stride,pad,*_=node['attrs'];bank_words=((min(32,co)+15)//16)*((ci+7)//8)*k*k
    assert ci<=512 and bank_words<=512,('core0x60004 unsupported weight-bank depth',sid,bank_words,512)
   elif node['op']=='Depthwise':
    sid,ci,co,k,stride,pad,*_=node['attrs'];assert ci==co and ci%8==0 and k==3,('unsupported O7 depthwise shape',sid,ci,co,k)
  if pc and hasattr(os,'add_dll_directory'):
   dependency=ROOT/'native_sources/pc_dependencies'
   if dependency.is_dir():self.dll_dir=os.add_dll_directory(str(dependency))
  self.lib=ctypes.CDLL(str(ROOT/'native_sources'/(library or ('native_queue_pc.dll' if pc else 'native_queue.so'))))
  self.lib.o7_create.argtypes=[ctypes.c_char_p,P,P,P];self.lib.o7_create.restype=P
  self.lib.o7_error.restype=ctypes.c_char_p
  self.lib.o7_run.argtypes=[P,P,P];self.lib.o7_run.restype=ctypes.c_int
  self.has_bgr=hasattr(self.lib,'o7_run_bgr')
  if self.has_bgr:self.lib.o7_run_bgr.argtypes=[P,P,P];self.lib.o7_run_bgr.restype=ctypes.c_int
  self.lib.o7_destroy.argtypes=[P];self.lib.o7_timers.argtypes=[P,P];self.lib.o7_profile.argtypes=[P,P];self.lib.o7_tensor.argtypes=[P,ctypes.c_int,P,ctypes.c_size_t]
  if pc:
   sys.path.insert(0,str(ROOT/'pc_intdw'))
   from hybrid_executor import YOLOHybridExecutor
   from integer_backend import TorchIntegerBackend
   from fixed_point import requantize
   self.backend=TorchIntegerBackend();self.ex=YOLOHybridExecutor(model_dir or ROOT/f'r{size}_intdw/model',self.backend,quantization_mode='fixed',fuse_activation=True)
   shapes=self.meta['shapes'];conv={n['attrs'][0]:n for n in self.meta['nodes'] if n['op'] in ('QuantConv','Depthwise')}
   def golden(sid,x,y):
    try:
     spec=self.ex.specs[sid];node=conv[sid];q=spec['quant'];shape=tuple(shapes[node['inputs'][0]][0]);outshape=tuple(shapes[node['outputs'][0]][0]);inp=np.ctypeslib.as_array((ctypes.c_int8*int(np.prod(shape))).from_address(x)).reshape(shape)
     acc=self.backend.execute(inp,self.ex.constants[q['weight']],self.ex.constants[q['bias']],spec,self.ex.constants)
     m,s=self.ex.fixed_parameters[sid];v=requantize(acc,m,s,int(self.ex.constants[q['output_zp']]))
     if node['attrs'][9]==2:v=self.ex.activation_tables[f'activation{sid}'][v.view(np.uint8)]
     ctypes.memmove(y,v.ctypes.data,int(np.prod(outshape)));return 0
    except Exception as e:self.failure=e;return -1
   self.callback=CB(golden);dp=cp=None
  else:
   from pynq import Overlay,PL,Clocks
   import hashlib
   manifest=json.loads((ROOT/'runtime_fast/queue_overlay_manifest.json').read_text());loaded=pathlib.Path(PL.bitfile_name or '')
   assert loaded.is_file() and hashlib.sha256(loaded.read_bytes()).hexdigest()==manifest['bit']['sha256'],'expected firmware is not loaded; programming forbidden'
   assert hashlib.sha256(loaded.with_suffix('.hwh').read_bytes()).hexdigest()==manifest['hwh']['sha256']
   self.overlay=Overlay(str(loaded),download=False);assert self.overlay.is_loaded()
   dn=[n for n,v in self.overlay.ip_dict.items() if ':axi_dma:' in v.get('type','')];cn=[n for n,v in self.overlay.ip_dict.items() if 'optimization_4_queue_top' in v.get('type','')];assert len(dn)==len(cn)==1
   self.dma=getattr(self.overlay,dn[0]);self.core=getattr(self.overlay,cn[0]);assert self.core.read(4)==0x60004 and abs(Clocks.fclk0_mhz-100)<.01
   dp=self.dma.mmio.array.ctypes.data;cp=self.core.mmio.array.ctypes.data
  self.handle=self.lib.o7_create(str(self.program/'graph.bin').encode(),dp,cp,ctypes.cast(self.callback,P) if self.callback else None)
  if not self.handle:raise RuntimeError(self.lib.o7_error().decode())
  shape=self.meta['shapes'][self.meta['names'][self.meta['output_id']]][0];self.raw=np.empty(shape,np.float32);self.timers=np.empty(16,np.float64);self.profile=np.empty(len(self.meta['nodes']),np.float64)
 def run(self,x):
  x=np.ascontiguousarray(x,np.float32)
  rc=self.lib.o7_run(self.handle,x.ctypes.data,self.raw.ctypes.data)
  if rc:raise RuntimeError(self.lib.o7_error().decode(),self.failure)
  self.lib.o7_timers(self.handle,self.timers.ctypes.data);self.lib.o7_profile(self.handle,self.profile.ctypes.data);return self.raw
 def tensor(self,name):
  shape,dtype=self.meta['shapes'][name];out=np.empty(shape,np.dtype(dtype));rc=self.lib.o7_tensor(self.handle,self.meta['names'].index(name),out.ctypes.data,out.nbytes)
  if rc:raise RuntimeError(self.lib.o7_error().decode())
  return out
 def run_image(self,image):
  import cv2
  st=time.perf_counter()
  h,w=image.shape[:2];gain=min(self.size/h,self.size/w);nw,nh=round(w*gain),round(h*gain)
  small=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR) if (nw,nh)!=(w,h) else image
  dx=(self.size-nw)/2;dy=(self.size-nh)/2;padded=cv2.copyMakeBorder(small,round(dy-.1),round(dy+.1),round(dx-.1),round(dx+.1),cv2.BORDER_CONSTANT,value=(114,114,114))
  self.last_python_preprocess_ms=(time.perf_counter()-st)*1000
  rc=self.lib.o7_run_bgr(self.handle,padded.ctypes.data,self.raw.ctypes.data)
  if rc:raise RuntimeError(self.lib.o7_error().decode(),self.failure)
  self.lib.o7_timers(self.handle,self.timers.ctypes.data);self.lib.o7_profile(self.handle,self.profile.ctypes.data);return self.raw
 def status(self):return dict(MM2S=hex(self.dma.read(4)),S2MM=hex(self.dma.read(0x34)),core=hex(self.core.read(0)),error=hex(self.core.read(0x64)),version=hex(self.core.read(4)))
 def quantization_mode(self,neon=False):
  self.lib.o7_set_quantization_mode.argtypes=[P,ctypes.c_int];self.lib.o7_set_quantization_mode(self.handle,int(neon))
 def memory(self):
  extended=hasattr(self.lib,'o7_memory_extended');fn=self.lib.o7_memory_extended if extended else self.lib.o7_memory;fn.argtypes=[P,P];out=np.zeros(8 if extended else 4,np.uint64);fn(self.handle,out.ctypes.data);return dict(zip(('CMA_TX_bytes','CMA_RX_bytes','host_tensor_reserved_bytes','host_plan_reserved_bytes','TX_BO_count','RX_BO_count','TX_layer_pool','RX_layer_pool'),map(int,out)))
 def close(self):
  if getattr(self,'handle',None):
   if not self.pc:
    states=[self.dma.read(a) for a in (4,0x34)]
    if any(not(s&3) for s in states):
     self.dma.write(0,self.dma.read(0)&~1);self.dma.write(0x30,self.dma.read(0x30)&~1);deadline=time.monotonic()+3
     while not all(self.dma.read(a)&1 for a in (4,0x34)):
      if time.monotonic()>deadline:raise RuntimeError('DMA halt timeout: retain engine/CMA for diagnosis')
      time.sleep(.001)
   self.lib.o7_destroy(self.handle);self.handle=None
