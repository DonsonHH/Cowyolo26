from pathlib import Path
from collections import OrderedDict
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=load(ROOT/'protocol/run_v1.json');v=load(ROOT/'results/independent_verification.json');s=load(ROOT/'delivery/results/record.json')
camera={r['frame0']:r for r in load(PROJECT/'pynq_periodic_joint_20261030/camera_delivery/manifest.json')}
producer_frames=received=overlap_cases=0;result=[]
for spec,case in zip(p['runs'],s['cases']):
 folder=ROOT/'delivery/results'/spec['run'];rows=load(folder/'timing_rows.json');packets=load(folder/'input_packets.json');prod=load(folder/'producer_record.json');assert len(packets)==len(rows)
 byframe={r['frame0']:r for r in prod['records']};rowmap={r['frame0']:r for r in rows};published_ns=[];records=[]
 if spec['policy'] in ['idle_gate','low_priority_parallel']:
  assert prod['status']=='JPEG_PRODUCER_COMPLETE' and not prod['thread_alive'] and prod['pinned_at_end'] is None
  assert [r['frame0'] for r in prod['records']]==list(range(8915,10874,5)) and len(prod['records'])==case['producer_read_frames']==392
  assert prod['producer_affinity']==[0,1]and isinstance(prod['producer_native_TID'],int)
  assert prod['peak_retained_frames']<=7
  maximum_JPEG=max(r['bytes'] for r in camera.values())
  assert prod['peak_retained_payload_bytes']<=7*maximum_JPEG and prod['peak_transient_payload_bytes']<=8*maximum_JPEG
  for slot,r in enumerate(prod['records']):
   assert r['slot']==slot and r['release_monotonic_ns']==case['clock_start_monotonic_ns']+slot*p['period_ns']
   assert r['release_monotonic_ns']<=r['read_started_monotonic_ns']<=r['read_finished_monotonic_ns']<=r['verified_monotonic_ns']<=r['published_monotonic_ns']
   assert r['JPEG_bytes']==camera[r['frame0']]['bytes'] and r['JPEG_sha256']==camera[r['frame0']]['sha256']
   assert r['retained_frames_after_publish']<=7
   assert r['retained_payload_bytes_after_publish']<=7*maximum_JPEG
   assert r['read_ms']==(r['read_finished_monotonic_ns']-r['read_started_monotonic_ns'])/1e6
   assert r['verification_ms']==(r['verified_monotonic_ns']-r['read_finished_monotonic_ns'])/1e6
   published_ns.append(r['published_monotonic_ns']);producer_frames+=1
  assert published_ns==sorted(published_ns)
 else:
  assert prod['status']=='SERIAL_INPUT_NO_PRODUCER' and prod['records']==[] and case['producer_read_frames']==0
 for row,packet in zip(rows,packets):
  frame=row['frame0'];assert packet['frame0']==frame and packet['slot']==row['slot'] and packet['release_monotonic_ns']==row['release_monotonic_ns']
  assert packet['release_monotonic_ns']<=packet['read_started_monotonic_ns']<=packet['read_finished_monotonic_ns']<=packet['verified_monotonic_ns']<=packet['published_monotonic_ns']<=packet['foreground_received_monotonic_ns']<=row['completed_monotonic_ns']
  assert row['JPEG_input_received_monotonic_ns']==packet['foreground_received_monotonic_ns']
  assert row['JPEG_frontend_read_ms']==(packet['foreground_received_monotonic_ns']-packet['foreground_wait_started_monotonic_ns'])/1e6
  assert packet['JPEG_bytes']==camera[frame]['bytes'] and packet['JPEG_sha256']==camera[frame]['sha256']
  model_end=row['started_monotonic_ns']+round(row['model_ms']*1000000)
  overlap=max(0,min(model_end,packet['read_finished_monotonic_ns'])-max(row['started_monotonic_ns'],packet['read_started_monotonic_ns']))/1e6
  if spec['policy'] in ['idle_gate','low_priority_parallel']:
   assert packet['source']=='async_producer' and row['JPEG_packet_source']=='async_producer'
   for key,value in byframe[frame].items():assert packet[key]==value
   overlap_cases+=overlap>0
  else:
   assert packet['source']=='serial_foreground' and packet['read_started_monotonic_ns']>=model_end
  records.append({'frame0':frame,'read_ms':(packet['read_finished_monotonic_ns']-packet['read_started_monotonic_ns'])/1e6,
   'verify_ms':(packet['verified_monotonic_ns']-packet['read_finished_monotonic_ns'])/1e6,'foreground_wait_ms':row['JPEG_frontend_read_ms'],
   'model_IO_overlap_ms':overlap,'release_to_received_ms':(packet['foreground_received_monotonic_ns']-packet['release_monotonic_ns'])/1e6})
  received+=1
 result.append({'run':spec['run'],'policy':spec['policy'],'producer_source_records':len(prod['records']),'main_received_packets':len(packets),
  'producer_peak_retained_frames':prod.get('peak_retained_frames',0),'producer_peak_retained_payload_bytes':prod.get('peak_retained_payload_bytes',0),
  'producer_peak_transient_payload_bytes':prod.get('peak_transient_payload_bytes',0),'packet_timing_rows':records})
assert producer_frames==1568 and received==v['actual_O8_timed_forwards']
record={'status':'ALL_RELEASE_GATED_PRODUCER_AND_FOREGROUND_RECEIPT_TIMESTAMPS_AND_SOURCE_HASHES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'producer_source_frames':producer_frames,'main_received_packets':received,'overlapping_model_IO_packet_cases':overlap_cases,'all_no_future_reads':True,
 'records':result,'bounds_not_total_system_memory':True,'new_model_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/producer_independent_verification.json';assert not f.exists();f.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='records'}))
