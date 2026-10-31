import pathlib,json,ctypes,time,numpy as np,pyxrt
from queue_device import QueueDevice
from native_ops import pointer
class QueueConv:
    output_kind='int8'
    def __init__(self,model_dir,native):
        self.native=native;self.core=QueueDevice();self.profile=[];self.fusion={};self.first=True;self.collect_state_counters=False
        model_dir=pathlib.Path(model_dir)
        with np.load(model_dir/'packed_weights.npz') as a:self.weights={k:a[k] for k in a.files}
        with np.load(model_dir/'fixed_parameters.npz') as a:self.parameters={k:a[k] for k in a.files}
        with np.load(model_dir/'activation_tables.npz') as a:self.activation_tables={k:a[k] for k in a.files}
        graph=json.loads((model_dir/'graph.json').read_text());self.outputs={s['id']:np.empty(s['output_shape'][1:],np.int8) for s in graph['convolutions'] if s['FPGA_supported']}
        self.plans={};self.empty_lut=np.zeros(256,np.uint8)
        for s in graph['convolutions']:
            if s['FPGA_supported']:
                blocks=np.array([[b['Cout_start'],b['Cout_actual'],b['chunks'][0]['offset']] for b in s['packed_blocks']],np.int32)
                h,w=s['output_shape'][-2:];count=len(blocks)*((h+15)//16)*((w+15)//16)
                rxwords=sum((b['Cout_actual']*min(16,h-y)*min(16,w-x)+3)//4 for b in s['packed_blocks'] for y in range(0,h,16) for x in range(0,w,16))
                self.plans[s['id']]=(blocks,np.empty((count,7),np.uint32),rxwords)
        p=ctypes.c_void_p;i=ctypes.c_int
        native.lib.pack_queue.argtypes=[p]*8+[i,p,ctypes.c_uint64,p];native.lib.pack_queue.restype=i
        native.lib.unpack_queue.argtypes=[p,p,i,i,p,i];native.lib.unpack_queue.restype=None
        native.lib.wait_queue.argtypes=[p]*4;native.lib.wait_queue.restype=i
    def execute(self,x,w,b,spec,constants):
        start=time.perf_counter();x=np.ascontiguousarray(x[0],np.int8);ci,h,wi=x.shape;identifier=spec['id'];q=spec['quant'];mode=2 if identifier in self.fusion else 1
        shape=np.array([ci,h,wi,spec['K'],spec['stride'],spec['padding'],int(constants[q['input_zp']]),int(constants[q['weight_zp']].reshape(-1)[0]),int(constants[q['output_zp']]),mode,1,identifier],np.int32)
        blocks,descs,rxwords=self.plans[identifier];lut=self.activation_tables['activation%d'%identifier] if mode==2 else self.empty_lut
        bias=np.ascontiguousarray(b,np.int32)
        packet_start=time.perf_counter();words=self.native.lib.pack_queue(pointer(x),pointer(bias),pointer(self.weights['conv%d'%identifier]),pointer(self.parameters['mult%d'%identifier]),pointer(self.parameters['shift%d'%identifier]),pointer(lut),pointer(shape),pointer(blocks),len(blocks),pointer(self.core.tx),len(self.core.tx),pointer(descs))
        pack=(time.perf_counter()-packet_start)*1000
        if words<=0 or rxwords>len(self.core.rx):raise RuntimeError('Queue packet capacity failure '+str(words))
        dma_start=time.perf_counter();self.core.tx.bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_TO_DEVICE,(words*4+63)&~63,0)
        rc=self.native.lib.submit_dma(pointer(self.core.dma.mmio.array),pointer(self.core.core.mmio.array),self.core.tx.physical_address,self.core.rx.physical_address,words*4,rxwords*4,int(self.first))
        if rc:raise RuntimeError('Queue DMA submit failed '+str(rc))
        self.first=False;counts=np.zeros(11,np.uint32);states=np.zeros(3,np.uint32)
        rc=self.native.lib.wait_queue(pointer(self.core.dma.mmio.array),pointer(self.core.core.mmio.array),pointer(counts),pointer(states))
        if rc or counts[6]!=words or counts[7]!=rxwords or counts[8]!=len(descs):raise RuntimeError('Queue DMA failure %d counts=%s states=%s'%(rc,counts.tolist(),states.tolist()))
        self.core.rx.bo.sync(pyxrt.xclBOSyncDirection.XCL_BO_SYNC_BO_FROM_DEVICE,(rxwords*4+63)&~63,0);dma_ms=(time.perf_counter()-dma_start)*1000
        out=self.outputs[identifier];unpack_start=time.perf_counter();self.native.lib.unpack_queue(pointer(self.core.rx),pointer(out),out.shape[1],out.shape[2],pointer(descs),len(descs));unpack=(time.perf_counter()-unpack_start)*1000
        self.profile.append(dict(name=spec['name'],ms=(time.perf_counter()-start)*1000,commands=1,tiles=len(descs),packing_ms=pack,DMA_FPGA_ms=dma_ms,unpack_ms=unpack,cycles=counts.tolist(),input_bytes=words*4,output_bytes=rxwords*4,weight_cache_hits=len(descs)-len(blocks)))
        self.profile[-1].update(DDR_read_bytes=int(self.core.core.read(0x180)),DDR_write_bytes=int(self.core.core.read(0x184)))
        if self.collect_state_counters:
            self.profile[-1]['state_cycles']=[int(self.core.core.read(0x100+4*i)) for i in range(32)]
        return out
    def close(self):self.core.close()
