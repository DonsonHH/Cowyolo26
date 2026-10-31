"""Attach and initialize freshly loaded Simple DMA; never programs the FPGA."""
import pathlib,json,hashlib,time
import numpy as np
def initialize(root):
 from pynq import Overlay,PL,Clocks,allocate
 root=pathlib.Path(root);m=json.loads((root/'hardware/accepted/firmware_manifest.json').read_text());bit=pathlib.Path(PL.bitfile_name or '')
 assert bit.is_file() and hashlib.sha256(bit.read_bytes()).hexdigest()==m['bit']['sha256'],'Expected O8 firmware is not loaded; explicit programming permission is required'
 assert hashlib.sha256(bit.with_suffix('.hwh').read_bytes()).hexdigest()==m['hwh']['sha256']
 o=Overlay(str(bit),download=False);dma=o.axi_dma_0;core=o.conv_accel_0;assert core.read(4)==0x80001 and core.read(8)==0x8000f and core.read(12)==131072 and abs(Clocks.fclk0_mhz-100)<.01
 assert core.read(0x64)==0 and not((dma.read(4)|dma.read(0x34))&0x770),'Device error: diagnose before retry'
 if dma.read(4)&2 and dma.read(0x34)&2:return dict(primed=False,core='0x80001',FCLK0_MHz=Clocks.fclk0_mhz)
 payload=np.concatenate([np.ones(8,np.uint32),np.ones(8,np.uint32),np.zeros(8,np.uint32),np.eye(8,dtype=np.int8).reshape(-1).view(np.uint32),np.arange(8,dtype=np.int8).view(np.uint32)]);cfg=np.array([8,8,1,1,1,1,1,1,0,0,len(payload),0,0,1,1,0,0x8fff0001],np.uint32);packet=np.concatenate([np.array([0x51434f34,1],np.uint32),cfg,payload]);tx=allocate(shape=packet.shape,dtype=np.uint32);rx=allocate(shape=(2,),dtype=np.uint32)
 try:
  tx[:]=packet;dma.recvchannel.transfer(rx);core.write(0,1);dma.sendchannel.transfer(tx);deadline=time.monotonic()+5
  while not(dma.read(4)&2 and dma.read(0x34)&2 and core.read(0)&2):
   assert not((dma.read(4)|dma.read(0x34))&0x770),'DMA initialization error'
   if time.monotonic()>deadline:raise RuntimeError('Bounded DMA initialization timeout')
  dma.sendchannel.wait();dma.recvchannel.wait();assert np.array_equal(rx.view(np.int8),np.arange(1,9,dtype=np.int8)) and core.read(0x64)==0
 finally:
  if dma.read(4)&2 and dma.read(0x34)&2:tx.freebuffer();rx.freebuffer()
 return dict(primed=True,core='0x80001',FCLK0_MHz=Clocks.fclk0_mhz,scope='8-word legacy initialization outside frame timing; no programming')
