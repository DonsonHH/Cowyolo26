import pathlib,json,hashlib,time,numpy as np
from pynq import Overlay,allocate,Clocks,PL
ROOT=pathlib.Path(__file__).resolve().parent
_failed_live_devices=[]
class QueueDevice:
    def __init__(self):
        manifest=json.loads((ROOT/'queue_overlay_manifest.json').read_text())
        for ext in ('bit','hwh'):assert hashlib.sha256((ROOT/('optimization_5_exact.'+ext)).read_bytes()).hexdigest()==manifest[ext]['sha256']
        loaded=pathlib.Path(PL.bitfile_name or '')
        if not loaded.is_file() or hashlib.sha256(loaded.read_bytes()).hexdigest()!=manifest['bit']['sha256']:
            raise RuntimeError('O5 firmware is not loaded; explicit programming permission required')
        assert hashlib.sha256(loaded.with_suffix('.hwh').read_bytes()).hexdigest()==manifest['hwh']['sha256']
        self.overlay=Overlay(str(loaded),download=False)
        if not self.overlay.is_loaded():raise RuntimeError('Queue Overlay not loaded; specific programming authorization required')
        entries=self.overlay.ip_dict;dn=[n for n,v in entries.items() if ':axi_dma:' in v.get('type','')];cn=[n for n,v in entries.items() if 'optimization_4_queue_top' in v.get('type','')]
        assert len(dn)==len(cn)==1
        self.core=getattr(self.overlay,cn[0]);assert self.core.read(4)==0x60004 and abs(Clocks.fclk0_mhz-100)<.01
        self.dma=getattr(self.overlay,dn[0]);self.tx=allocate((1048576,),dtype=np.uint32)
        try:self.rx=allocate((524288,),dtype=np.uint32)
        except Exception:self.tx.freebuffer();raise
        self.closed=False
        self.info=dict(dma_name=dn[0],core_name=cn[0],version=self.core.read(4),FCLK0_MHz=Clocks.fclk0_mhz,
                       DMA_base=entries[dn[0]]['phys_addr'],core_base=entries[cn[0]]['phys_addr'],CMA_bytes=self.tx.nbytes+self.rx.nbytes,
                       DMA_range=entries[dn[0]]['addr_range'],core_range=entries[cn[0]]['addr_range'],
                       DMA_driver=type(self.dma).__module__+'.'+type(self.dma).__name__,
                       core_driver=type(self.core).__module__+'.'+type(self.core).__name__,
                       DMA_parameters=entries[dn[0]]['parameters'],overlay_downloaded=False)
    def status(self):
        return dict(MM2S=hex(self.dma.read(4)),S2MM=hex(self.dma.read(0x34)),
                    core=hex(self.core.read(0)),error=hex(self.core.read(0x64)),
                    TX_BTT=self.dma.read(0x28),RX_BTT=self.dma.read(0x58))
    def close(self):
        if self.closed:return
        # An exceptional DMA may still own CMA. Halt both channels with a
        # deadline before freeing buffers; never reset an active transfer.
        states=[self.dma.read(a) for a in (4,0x34)]
        if any(not(s&3) for s in states):
            self.dma.write(0,self.dma.read(0)&~1);self.dma.write(0x30,self.dma.read(0x30)&~1)
            deadline=time.monotonic()+3
            while not all(self.dma.read(a)&1 for a in (4,0x34)):
                if time.monotonic()>deadline:
                    _failed_live_devices.append(self)
                    raise RuntimeError('DMA halt timeout; retain CMA until authorized recovery: '+str(self.status()))
                time.sleep(.001)
        self.tx.freebuffer();self.rx.freebuffer();self.closed=True
