"""Release-gated JPEG acquisition; bounded payload bank plus one pinned frame."""
from pathlib import Path
from collections import OrderedDict
import threading,time,hashlib,traceback,os

class JPEGProducer:
    def __init__(self, rows, root, start_ns, period_ns, reader=None):
        self.rows=rows;self.root=Path(root);self.start_ns=start_ns;self.period_ns=period_ns
        self.reader=reader or (lambda p:p.read_bytes())
        self.condition=threading.Condition();self.stop_event=threading.Event();self.bank=OrderedDict()
        self.pinned=None;self.records=[];self.error=None;self.finished=False
        self.peak_retained_bytes=0;self.peak_transient_bytes=0;self.peak_retained_frames=0
        self.thread=threading.Thread(target=self._run,name='released-JPEG-input',daemon=False)

    def start(self):
        self.thread.start()

    def _prune(self):
        latest=set(list(self.bank)[-6:])
        for frame in list(self.bank):
            if frame not in latest and frame!=self.pinned:del self.bank[frame]
        assert len(self.bank)<=7
        self.peak_retained_frames=max(self.peak_retained_frames,len(self.bank))
        self.peak_retained_bytes=max(self.peak_retained_bytes,sum(len(v['payload']) for v in self.bank.values()))

    def pin(self, frame):
        with self.condition:
            assert self.pinned is None
            self.pinned=frame

    def take(self, frame, timeout=30):
        limit=time.monotonic()+timeout
        with self.condition:
            assert self.pinned==frame
            while frame not in self.bank:
                if self.error:raise RuntimeError(self.error['error'])
                if self.finished:raise RuntimeError('Producer_finished_without_requested_frame:'+str(frame))
                remaining=limit-time.monotonic()
                if remaining<=0:raise TimeoutError('JPEG_input_wait:'+str(frame))
                self.condition.wait(min(.25,remaining))
            packet=self.bank[frame];self.pinned=None;self._prune()
            return packet

    def _run(self):
        self.native_TID=threading.get_native_id();self.actual_affinity=sorted(os.sched_getaffinity(0))if hasattr(os,"sched_getaffinity")else None
        try:
            for slot,row in enumerate(self.rows):
                release=self.start_ns+slot*self.period_ns
                while True:
                    now=time.monotonic_ns()
                    if now>=release:break
                    if self.stop_event.wait((release-now)/1e9):return
                if self.stop_event.is_set():return
                started=time.monotonic_ns();cpu=time.thread_time_ns();assert started>=release
                payload=self.reader(self.root/row['file']);read_end=time.monotonic_ns()
                digest=hashlib.sha256(payload).hexdigest();verified=time.monotonic_ns();cpu_end=time.thread_time_ns()
                assert len(payload)==row['bytes'] and digest==row['sha256']
                with self.condition:
                    published=time.monotonic_ns()
                    record={'slot':slot,'frame0':row['frame0'],'release_monotonic_ns':release,
                            'read_started_monotonic_ns':started,'read_finished_monotonic_ns':read_end,
                            'verified_monotonic_ns':verified,'published_monotonic_ns':published,
                            'JPEG_bytes':len(payload),'JPEG_sha256':digest,
                            'read_ms':(read_end-started)/1e6,'verification_ms':(verified-read_end)/1e6,
                            'read_and_verification_thread_CPU_ms':(cpu_end-cpu)/1e6}
                    self.peak_transient_bytes=max(self.peak_transient_bytes,sum(len(v['payload']) for v in self.bank.values())+len(payload))
                    self.bank[row['frame0']]={'payload':payload,'record':record}
                    self._prune();record['retained_frames_after_publish']=len(self.bank)
                    record['retained_payload_bytes_after_publish']=sum(len(v['payload']) for v in self.bank.values())
                    self.records.append(record);self.condition.notify_all()
                del payload
        except BaseException as e:
            with self.condition:self.error={'error':repr(e),'traceback':traceback.format_exc()};self.condition.notify_all()
        finally:
            with self.condition:self.finished=True;self.condition.notify_all()

    def finish(self, timeout=30):
        self.thread.join(timeout)
        if self.thread.is_alive():raise TimeoutError('JPEG_producer_still_running')
        if self.error:raise RuntimeError(self.error['error'])
        return self.summary()

    def close(self, timeout=30):
        self.stop_event.set()
        return self.finish(timeout)

    def summary(self):
        return {'status':'JPEG_PRODUCER_COMPLETE' if self.finished and not self.error and not self.thread.is_alive() else 'NOT_COMPLETE',
                'thread_alive':self.thread.is_alive(),'records':self.records,'error':self.error,
                'peak_retained_frames':self.peak_retained_frames,'peak_retained_payload_bytes':self.peak_retained_bytes,
                'peak_transient_payload_bytes':self.peak_transient_bytes,'pinned_at_end':self.pinned,'producer_native_TID':getattr(self,'native_TID',None),'producer_affinity':getattr(self,'actual_affinity',None)}
