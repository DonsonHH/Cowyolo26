"""Causality, bounded slow consumer, retained request, and failure propagation."""
from jpeg_producer import JPEGProducer
import hashlib,time,json,threading
blob=b'actual-input-producer-test';digest=hashlib.sha256(blob).hexdigest()
rows=[{'frame0':i*5,'file':str(i),'bytes':len(blob),'sha256':digest} for i in range(24)]
start=time.monotonic_ns()+10000000
p=JPEGProducer(rows,'.',start,1000000,reader=lambda _:blob);p.pin(0);p.start();s=p.finish(timeout=2)
assert len(s['records'])==24 and all(r['read_started_monotonic_ns']>=r['release_monotonic_ns'] for r in s['records'])
assert s['peak_retained_frames']==7 and len(p.bank)==7 and 0 in p.bank
assert p.take(0)['payload']==blob and len(p.bank)==6
assert all(r['retained_frames_after_publish']<=7 for r in s['records'])
bad=JPEGProducer(rows[:1],'.',time.monotonic_ns(),1000000,reader=lambda _:b'wrong');bad.pin(0);bad.start()
try:
    bad.take(0,timeout=1);raise AssertionError('bad hash accepted')
except RuntimeError:pass
try:bad.finish(timeout=1)
except RuntimeError:pass
assert not bad.thread.is_alive()
stopped=JPEGProducer(rows,'.',time.monotonic_ns()+1000000000,1000000,reader=lambda _:blob);stopped.start();stopped.close(timeout=1)
assert stopped.records==[] and not stopped.thread.is_alive()
print(json.dumps({'status':'PRODUCER_RELEASE_BOUND_PIN_FAILURE_AND_STOP_BEHAVIOR_PASS','source_frames':24,'future_reads':0,'peak_retained_frames':7,'real_board_or_model_forward':False}))
