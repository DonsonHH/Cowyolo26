"""Bounded live abort/reset and invalid-local-consumer recovery; no programming."""
import pathlib,sys,json,time,fcntl,traceback
sys.dont_write_bytecode=True
import numpy as np
from pynq import Overlay,PL,allocate
R=pathlib.Path('/home/xilinx/jupyter_notebooks');D=R/'yolo26_optimization_8';O=D/'reports'/('recovery_'+str(time.time_ns()));O.mkdir();lock=(R/'yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);o=Overlay(PL.bitfile_name,download=False);dma=o.axi_dma_0;core=o.conv_accel_0;assert core.read(4)==0x80001;rows=[]
def state():return dict(tx=hex(dma.read(4)),rx=hex(dma.read(0x34)),core=hex(core.read(0)),error=hex(core.read(0x64)))
initial=state();core.write(0,16);dma.write(0,4);deadline=time.monotonic()+3
while dma.read(0)&4 or not(dma.read(4)&1 and dma.read(0x34)&1):
 if time.monotonic()>deadline:raise RuntimeError('Pre-test reset/halt timeout')
o=Overlay(PL.bitfile_name,download=False);dma=o.axi_dma_0;core=o.conv_accel_0;rows.append(dict(test='pre-test reset after earlier software busy-mask mistake',initial=initial,after=state(),programming=False));rx=allocate(shape=(1,),dtype=np.uint32)
try:
 before=state();dma.recvchannel.transfer(rx);core.write(0,1);deadline=time.monotonic()+1
 while not(core.read(0)&4):
  if time.monotonic()>deadline:raise RuntimeError('queue did not start')
 live=state();core.write(0,16);dma.write(0,4);deadline=time.monotonic()+3
 while dma.read(0)&4 or not(dma.read(4)&1 and dma.read(0x34)&1):
  if time.monotonic()>deadline:raise RuntimeError('DMA reset/halt bounded timeout; preserve RX BO')
 rows.append(dict(test='abort waiting-for-header with live S2MM',before=before,live=live,after_reset=state(),BO_freed_only_after_both_halted=True,programming=False));rx.freebuffer();rx=None
 o=Overlay(PL.bitfile_name,download=False);dma=o.axi_dma_0;core=o.conv_accel_0;assert core.read(0x64)==0
 def transfer(x,y,expected_error=0):
  tx=allocate(shape=x.shape,dtype=np.uint32);out=allocate(shape=y.shape,dtype=np.uint32)
  try:
   tx[:]=x;out[:]=0xDEADBEEF;dma.recvchannel.transfer(out);core.write(0,1);dma.sendchannel.transfer(tx);deadline=time.monotonic()+15
   while not(dma.read(4)&2 and dma.read(0x34)&2 and core.read(0)&2):
    assert not((dma.read(4)|dma.read(0x34))&0x770)
    if time.monotonic()>deadline:raise RuntimeError(('bounded replay timeout',state()))
   dma.sendchannel.wait();dma.recvchannel.wait();assert np.array_equal(out,y),(int(np.count_nonzero(out!=y)),state());assert core.read(0x64)==expected_error
   return state()
  finally:
   if dma.read(4)&2 and dma.read(0x34)&2:tx.freebuffer();out.freebuffer()
 payload=np.concatenate([np.ones(8,np.uint32),np.ones(8,np.uint32),np.zeros(8,np.uint32),np.eye(8,dtype=np.int8).reshape(-1).view(np.uint32),np.arange(8,dtype=np.int8).view(np.uint32)]);cfg=np.array([8,8,1,1,1,1,1,1,0,0,len(payload),0,0,1,1,0,0x8fff0001],np.uint32);packet=np.concatenate([np.array([0x51434f34,1],np.uint32),cfg,payload]);rows.append(dict(test='legacy initialization after abort',after=transfer(packet,np.arange(1,9,dtype=np.int8).view(np.uint32))))
 S=D/'tests/board_vectors/20261019_155244_966520';read=lambda n:np.loadtxt(S/n,dtype=np.uint32,converters={0:lambda v:int(v,16)}).reshape(-1);pair=read('r192_21_22_input.hex');expected=read('r192_21_22_output.hex');pos=0
 while not int(pair[pos+1])&2:pos+=28+int(pair[pos+19])
 assert pos<len(pair);consumer=pair[pos:].copy();rows.append(dict(test='local consumer after reset without committed producer must reject',after=transfer(consumer,np.array([0xBAD00801],np.uint32),0x802)))
 rows.append(dict(test='valid resident pair after error',after=transfer(pair,expected),correct_words=len(expected),mismatches=0))
 result=dict(status='PASS',rows=rows,scope='AXI-Lite soft_reset and documented AXI DMA reset only; exclusive lock; bounded waits; no FPGA reprogramming or system change')
except BaseException:
 result=dict(status='FAIL',rows=rows,failure=traceback.format_exc());raise
finally:
 if rx is not None:
  core.write(0,16);dma.write(0,4);cleanup_deadline=time.monotonic()+3
  while dma.read(0)&4 or not(dma.read(4)&1 and dma.read(0x34)&1):
   if time.monotonic()>cleanup_deadline:raise RuntimeError('cleanup could not confirm DMA halted; do not reuse device')
  rx.freebuffer()
 (O/'summary.json').write_text(json.dumps(result,indent=2));print('O8_RECOVERY_REPORT',json.dumps(result),O,flush=True)
