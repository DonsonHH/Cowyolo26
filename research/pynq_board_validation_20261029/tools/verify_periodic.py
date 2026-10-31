"""Independent offered-slot/deadline accounting and real raw-array checks."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib,tarfile,math,statistics,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['jpeg','framebank'],required=True);p.add_argument('--use-existing-delivery',action='store_true');a=p.parse_args()
bank=a.mode=='framebank';prefix='framebank' if bank else 'stream';run='framebank_replay' if bank else 'stream_replay'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
transfer=load(ROOT/'evidence'/(prefix+'_transfer.json'));archive=ROOT/(run+'_complete.tar.gz');assert archive.stat().st_size==transfer['bytes'] and sha(archive)==transfer['sha256']
out=ROOT/(prefix+'_delivery')
if a.use_existing_delivery:assert out.is_dir()
else:out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==transfer['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(out/member.name).resolve();assert file.is_relative_to(out.resolve())
        if a.use_existing_delivery:assert file.is_file() and file.read_bytes()==tar.extractfile(member).read()
        else:
            assert not file.exists();file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
manifest=load(out/(prefix+'_artifact_manifest.json'));assert len(manifest)==transfer['manifest_files']
for r in manifest:
    file=out/r['relative_file'];assert file.stat().st_size==r['bytes'] and sha(file)==r['sha256']
protocol=load(ROOT/'protocol'/(prefix+'_v1.json'));assert sha(ROOT/'protocol'/(prefix+'_v1.json'))==sha(out/(prefix+'_protocol.json'))
script=ROOT/'tools'/('board_framebank_replay.py' if bank else 'board_stream_replay.py');assert sha(out/script.name)==sha(script)
record=load(out/run/'record.json');terminal=load(out/run/'terminal.json');assert record['status']==terminal['status']=='ALL3_REAL_BOARD_PERIODIC_LOWRES_REPLAYS_COMPLETED'
assert terminal['record_sha256']==sha(out/run/'record.json') and record['protocol_sha256']==sha(ROOT/'protocol'/(prefix+'_v1.json'))
assert record['close_error'] is None and record['current_cow_finetuned_weights_loaded'] is False and record['background_identity_active'] is False and record['foreground_tracking_active'] is False and record['camera_hardware_active'] is False
parent=load(ROOT/'protocol/board_v2.json');assert record['boot_id']==parent['recovered_boot_id']
assert record['final_known_O8_bit_sha256']==parent['O8_bit_sha256']
prior={};prior_inputs={};comparison_rows=0;compared_query_conditions=set();bank_inputs={}
if bank:
    previous=load(ROOT/'stream_delivery/stream_replay/record.json')
    assert protocol['source_stream_archive_sha256']==sha(ROOT/'stream_replay_complete.tar.gz') and protocol['parent_stream_protocol_sha256']==sha(ROOT/'protocol/stream_v1.json')
    for case in previous['cases']:
        for row in case['rows']:
            key=(case['size'],row['query_id']);prior_inputs[row['query_id']]=row['actual_input_rotated_BGR_sha256']
            file=ROOT/'stream_delivery/stream_replay'/('s'+str(case['size']))/row['raw_file']
            raw=np.load(file)
            if key in prior:assert np.array_equal(prior[key],raw)
            prior[key]=raw
    path=out/run/record['framebank']['actual_lowres_inputs_file'];assert sha(path)==record['framebank']['file_sha256']
    with np.load(path) as arrays:bank_inputs={k:arrays[k] for k in arrays.files}
    assert set(bank_inputs)=={s['query_id'] for s in parent['source_images']} and sum(v.nbytes for v in bank_inputs.values())==record['framebank']['total_BGR_bytes']==2073600
    for name,array in bank_inputs.items():
        assert array.shape==(180,320,3) and array.dtype==np.uint8
        assert hashlib.sha256(array.tobytes()).hexdigest()==record['framebank']['native_BGR_pixel_sha256'][name]
        oriented=np.ascontiguousarray(array.transpose(1,0,2)[:,::-1])
        if name in prior_inputs:assert hashlib.sha256(oriented.tobytes()).hexdigest()==prior_inputs[name]
def quantile(values,q):
    values=sorted(values);point=(len(values)-1)*q;lo=math.floor(point);hi=math.ceil(point)
    return values[lo]+(values[hi]-values[lo])*(point-lo)
maximum_stats_error=0.
def checkstats(values,actual):
    global maximum_stats_error
    expected={'samples':len(values),'mean_ms':statistics.mean(values),'p50_ms':statistics.median(values),'p95_ms':quantile(values,.95),'maximum_ms':max(values),'above200ms':sum(v>200 for v in values)}
    assert set(expected)==set(actual)
    for k,v in expected.items():difference=abs(v-actual[k]);assert difference<1e-8;maximum_stats_error=max(maximum_stats_error,difference)
    return expected
results=[];allrows=[];processed_total=skipped_total=forwards=0
for case in record['cases']:
    size=case['size'];folder=out/run/('s'+str(size));assert case==load(folder/'summary.json') and case['engine']==parent['engines'][str(size)]
    assert len(case['warmups'])==protocol['warmups']==2 and case['safe_close_complete'] is True
    slots=[r['offered_slot'] for r in case['rows']];assert slots==sorted(set(slots))
    assert sorted(slots+case['skipped_slots'])==list(range(100)) and len(set(slots+case['skipped_slots']))==100
    assert case['offered']==100 and case['processed']==len(slots) and case['skipped']==len(case['skipped_slots'])
    epoch=case['epoch_monotonic_ns'];lastfinish=epoch;period=protocol['period_ns'];deadlines=above200=0;seen={};instrumentation_residuals=[]
    for row in case['rows']:
        source=parent['source_images'][row['offered_slot']%12]
        assert row['query_id']==source['query_id'] and row['source_frame0']==source['source_frame0'] and row['source_photo_sha256']==source['sha256']
        assert row['release_ns']==epoch+row['offered_slot']*period and row['deadline_ns']==row['release_ns']+period
        assert row['release_ns']<=row['start_ns']<row['finish_ns'] and row['start_ns']>=lastfinish;lastfinish=row['finish_ns']
        key='frontend_copy_rotation_detector_ms' if bank else 'frontend_read_rotation_detector_ms'
        elapsed=(row['finish_ns']-row['start_ns'])/1e6;age=(row['finish_ns']-row['release_ns'])/1e6
        assert abs(elapsed-row[key])<1e-8 and abs(age-row['capture_age_since_offered_release_ms'])<1e-8
        assert abs((row['start_ns']-row['release_ns'])/1e6-row['start_delay_ms'])<1e-8
        assert row['deadline_miss']==(row['finish_ns']>row['deadline_ns']);deadlines+=row['deadline_miss'];above200+=elapsed>200
        readkey='lowres_input_copy_ms' if bank else 'photo_read_ms'
        detail=row[readkey]+row['native_CW_rotation_ms']+row['graph_and_preprocess_copy_ms']+row['decode_ms']
        # The outer interval includes the status reads and Python return after
        # the inner timestamp. Preserve that overhead rather than subtract it.
        residual=elapsed-detail;assert residual>=-1e-8;instrumentation_residuals.append(residual)
        file=folder/row['raw_file'];assert sha(file)==row['raw_file_sha256'];raw=np.load(file)
        assert raw.shape==(1,300,6) and raw.dtype==np.float32 and np.isfinite(raw).all() and hashlib.sha256(raw.tobytes()).hexdigest()==row['raw_array_sha256']
        if row['query_id'] in seen:assert np.array_equal(raw,seen[row['query_id']])
        seen[row['query_id']]=raw
        if bank:
            image=bank_inputs[row['query_id']];oriented=np.ascontiguousarray(image.transpose(1,0,2)[:,::-1])
            assert hashlib.sha256(oriented.tobytes()).hexdigest()==row['actual_input_rotated_BGR_sha256']
            if (size,row['query_id']) in prior:assert np.array_equal(raw,prior[(size,row['query_id'])]);comparison_rows+=1;compared_query_conditions.add((size,row['query_id']))
        status=row['hardware_status'];assert status['error']=='0x0' and all(int(status[k],16)&2 for k in ['MM2S','S2MM'])
        assert not any(int(status[k],16)&0x770 for k in ['MM2S','S2MM'])
        allrows.append({'mode':a.mode,'size':size,'engine':case['engine'],**{k:v for k,v in row.items() if k in ['offered_slot','query_id','source_frame0',readkey,'native_CW_rotation_ms',key,'start_delay_ms','capture_age_since_offered_release_ms','deadline_miss']}})
    assert case['on_time']==len(slots)-deadlines and case['deadline_misses']==deadlines
    assert case['observed_end_monotonic_ns']>=lastfinish
    duration=max(100*period,case['observed_end_monotonic_ns']-epoch)/1e9
    assert abs(case['observation_window_s']-duration)<1e-10 and abs(case['observed_processed_fps']-len(slots)/duration)<1e-10
    key='frontend_copy_rotation_detector_ms' if bank else 'frontend_read_rotation_detector_ms'
    frontend=checkstats([r[key] for r in case['rows']],case['frontend_statistics'])
    checkstats([r['capture_age_since_offered_release_ms'] for r in case['rows']],case['age_statistics'])
    assert frontend['above200ms']==above200;processed_total+=len(slots);skipped_total+=case['skipped'];forwards+=len(slots)+2
    readkey='lowres_input_copy_ms' if bank else 'photo_read_ms'
    results.append({'size':size,'engine':case['engine'],'processed':len(slots),'skipped':case['skipped'],'offered':100,'deadline_misses':deadlines,
     'on_time':len(slots)-deadlines,'observation_window_s':duration,'observed_processed_fps':len(slots)/duration,'frontend':frontend,
     'mean_input_read_or_copy_ms':statistics.mean(r[readkey] for r in case['rows']),
     'capture_is_real_camera':False,'source_query_conditions':len(seen),
     'mean_included_instrumentation_residual_ms':statistics.mean(instrumentation_residuals),
     'maximum_included_instrumentation_residual_ms':max(instrumentation_residuals)})
assert processed_total+skipped_total==300 and forwards==record['total_actual_image_forwards']==terminal['total_actual_image_forwards']
result={'status':'ACTUAL_PERIODIC_BOARD_TIMESTAMPS_SLOT_PARTITION_RAW_AND_STATISTICS_INDEPENDENTLY_VERIFIED',
 'mode':a.mode,'created_host_UTC':datetime.now(timezone.utc).isoformat(),'archive_sha256':sha(archive),'archive_members':len(members),
 'offered_slots':300,'actual_processed_raw_arrays':processed_total,'skipped_slots':skipped_total,'actual_image_forwards_with6warmups':forwards,
 'maximum_statistics_delta':maximum_stats_error,'cases':results,'same_pixel_prior_raw_comparison_rows':comparison_rows,
 'same_pixel_prior_unique_model_query_conditions':len(compared_query_conditions),'framebank_input_images_verified':len(bank_inputs),
 'real_camera_capture':False,'foreground_tracking_active':False,'background_identity_active':False,
 'current_cow_finetuned_weights_deployed':False,'joint_foreground_background_5FPS_proven':False,'whole_goal_complete':False}
save(ROOT/'results'/('independent_'+prefix+'_verification.json'),result)
with (ROOT/'results'/(prefix+'_samples.csv')).open('x',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(allrows[0]));w.writeheader();w.writerows(allrows)
print(json.dumps(result))
