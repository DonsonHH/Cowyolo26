"""Verify closed on-board artifacts; recompute statistics and decode raw arrays."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,math,statistics,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,indent=2)+'\n')
transfer=load(ROOT/'evidence/profiles_transfer.json');archive=ROOT/'profiles_complete.tar.gz';assert archive.stat().st_size==transfer['bytes'] and sha(archive)==transfer['sha256']
out=ROOT/'delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==transfer['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        path=(out/member.name).resolve();assert path.is_relative_to(out.resolve()) and not path.exists()
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(member).read())
manifest=load(out/'profile_artifact_manifest.json');assert len(manifest)==transfer['manifest_files']
for row in manifest:
    p=out/row['relative_file'];assert p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
assert sha(out/'protocol.json')==sha(ROOT/'protocol/board_v2.json') and sha(out/'board_profile.py')==sha(ROOT/'tools/board_profile.py')
protocol=load(out/'protocol.json');rows=[];cases=[];arrays={};shapechecks=decoded=repeatchecks=0;max_stats_delta=0.
def quantile(values,q):
    a=sorted(values);position=(len(a)-1)*q;lo=math.floor(position);hi=math.ceil(position)
    return a[lo]+(a[hi]-a[lo])*(position-lo)
def checkstats(values,actual):
    global max_stats_delta
    expected={'samples':len(values),'mean_ms':math.fsum(values)/len(values),'p50_ms':statistics.median(values),
              'p95_ms':quantile(values,.95),'maximum_ms':max(values),'fps_from_mean':1000/(math.fsum(values)/len(values)),
              'above200ms':sum(v>200 for v in values)}
    assert set(expected)==set(actual)
    for k,v in expected.items():delta=abs(v-actual[k]);assert delta<1e-8,(k,v,actual[k]);max_stats_delta=max(max_stats_delta,delta)
    return expected
for run in ['probe192','formal192','formal256','formal320']:
    record=load(out/run/'record.json');terminal=load(out/run/'terminal.json');probe=run=='probe192';size=record['size']
    assert record['status']==terminal['status']==('PROBE_COMPLETED' if probe else 'PROFILE_COMPLETED')
    assert record['close_error'] is None and terminal['record_sha256']==sha(out/run/'record.json')
    assert record['boot_id']==terminal['boot_id']==protocol['recovered_boot_id'] and terminal['PID']==record['PID']
    assert len(record['rows'])==terminal['samples']==(1 if probe else 32) and len(record['warmups'])==(0 if probe else 2)
    assert record['protocol_sha256']==sha(ROOT/'protocol/board_v2.json') and record['engine']==protocol['engines'][str(size)]
    assert record['current_cow_finetuned_checkpoint_loaded'] is False and record['background_identity_active'] is False and record['camera_active'] is False
    times=[r['monotonic_ns'] for r in record['stages']];assert times==sorted(times)
    assert record['stages'][-1]['stage']=='safe_graph_close_complete' and record['finished_monotonic_ns']>=times[-1]
    expected_count=1 if probe else 32;raws=[]
    for index,row in enumerate(record['rows']):
        source=protocol['source_images'][index] if index<12 else protocol['source_images'][9]
        assert row['index']==index and row['query_id']==source['query_id'] and row['source_frame0']==source['source_frame0'] and row['source_photo_sha256']==source['sha256']
        assert row==load(out/run/('row_'+str(index).zfill(2)+'.json'))
        file=out/run/row['raw_file'];assert sha(file)==row['raw_file_sha256']
        raw=np.load(file);assert raw.shape==(1,300,6) and raw.dtype==np.float32 and np.isfinite(raw).all();shapechecks+=1
        assert hashlib.sha256(raw.tobytes()).hexdigest()==row['raw_array_sha256']
        assert np.all((raw[0,:,4]>=0)&(raw[0,:,4]<=1)) and np.all((raw[0,:,5]>=0)&(raw[0,:,5]<80)) and np.all(raw[0,:,5]==np.rint(raw[0,:,5]))
        # Independently restore network boxes to the CW-rotated2560x1440 image.
        chosen=raw[0,raw[0,:,4]>=.2].astype(np.float64);gain=size/2560
        px=round((size-1440*gain)/2-.1);py=round((size-2560*gain)/2-.1)
        chosen[:,[0,2]]=(chosen[:,[0,2]]-px)/gain;chosen[:,[1,3]]=(chosen[:,[1,3]]-py)/gain
        chosen[:,[0,2]]=np.clip(chosen[:,[0,2]],0,1440);chosen[:,[1,3]]=np.clip(chosen[:,[1,3]],0,2560)
        cow=chosen[chosen[:,5]==19];actual=np.asarray(row['cow_boxes_rotated_native'],float).reshape(-1,6)
        assert cow.shape==actual.shape and (not cow.size or np.max(np.abs(cow-actual))<.001)
        assert len(chosen)==row['all_class_detections'];decoded+=len(chosen)
        status=row['hardware_status'];assert status['error']=='0x0' and all(int(status[k],16)&2 for k in ['MM2S','S2MM'])
        assert not any(int(status[k],16)&0x770 for k in ['MM2S','S2MM'])
        if size in [192,256]:assert status['version']=='0x80001' and record['device_initialization']['FCLK0_MHz']==100.0
        assert abs(row['detector_e2e_ms']-row['graph_and_preprocess_copy_ms']-row['decode_ms'])<1e-8
        assert abs(row['photo_rotation_detector_ms']-row['photo_read_ms']-row['native_CW_rotation_ms']-row['detector_e2e_ms'])<1e-8
        for key in ['detector_e2e_ms','photo_read_ms','native_CW_rotation_ms','decode_ms','graph_and_preprocess_copy_ms','python_preprocess_ms']:assert math.isfinite(row[key]) and row[key]>=0
        raws.append(raw);rows.append({'run':run,'size':size,'engine':record['engine'],**{k:row[k] for k in ['index','query_id','source_frame0','fixed_E010_repeat','photo_read_ms','native_CW_rotation_ms','python_preprocess_ms','graph_and_preprocess_copy_ms','decode_ms','detector_e2e_ms','photo_rotation_detector_ms','all_class_detections']},'cow_detections':len(cow)})
    for i in range(12,len(raws)):
        assert np.array_equal(raws[9],raws[i]);repeatchecks+=1
    assert record['repeat_raw_maximum_absolute_delta']==0
    arrays[run]=raws
    detector=checkstats([r['detector_e2e_ms'] for r in record['rows']],record['detector_e2e_statistics'])
    combined=checkstats([r['photo_rotation_detector_ms'] for r in record['rows']],record['photo_rotation_detector_statistics'])
    if not probe:checkstats([r['detector_e2e_ms'] for r in record['rows'][12:]],record['fixed_E010_detector_statistics'])
    cases.append({'run':run,'size':size,'probe_only':probe,'engine':record['engine'],'samples':len(raws),'warmups':len(record['warmups']),
                  'detector':detector,'photo_rotation_detector':combined,'mean_photo_read_ms':statistics.mean(r['photo_read_ms'] for r in record['rows']),
                  'mean_native_rotation_ms':statistics.mean(r['native_CW_rotation_ms'] for r in record['rows']),
                  'cow_present_photos':sum(bool(r['cow_boxes_rotated_native']) for r in record['rows'][:12]),
                  'stages_monotonic':True,'record_sha256':sha(out/run/'record.json'),'raw_decoding_is_not_accuracy_ground_truth':True})
assert shapechecks==97 and repeatchecks==60 and np.array_equal(arrays['probe192'][0],arrays['formal192'][0])
previous=load(out/'recovery_record.json');oldarchive=ROOT/'prior_interrupted_test.tar.gz'
assert oldarchive.stat().st_size==previous['archive_bytes'] and sha(oldarchive)==previous['archive_sha256']
oldmanifest=load(out/'prior_interrupted_manifest.json');assert len(oldmanifest)==39 and sha(out/'prior_interrupted_manifest.json')==previous['prior_manifest_sha256']
old_compare=0
with tarfile.open(oldarchive) as tar:
    assert len(tar.getmembers())==39
    for r in oldmanifest:
        b=tar.extractfile(r['relative']).read();assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256']
        if r['relative'].startswith('results/192_') and r['relative'].endswith('_raw.npy'):
            import io
            actual=np.load(io.BytesIO(b));identity=r['relative'][len('results/192_'):-len('_raw.npy')]
            index=next(i for i,x in enumerate(protocol['source_images']) if x['query_id']==identity)
            assert np.array_equal(actual,arrays['formal192'][index]);old_compare+=1
assert old_compare==12
state=load(out/'board_state_after_profiles.json');assert state['probe_and_formal_image_forwards']==103 and state['PL_after_bit_sha256']==protocol['O8_bit_sha256']
assert all(r['status']==('PROBE_COMPLETED' if r['run']=='probe192' else 'PROFILE_COMPLETED') for r in state['profiles_terminal'])
result={'status':'THREE_REAL_BOARD_PROFILES97_RAW_ARRAYS96_FORMAL_ROWS_AND12_PRIOR_RAW_REPEATS_INDEPENDENTLY_VERIFIED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'archive_bytes':transfer['bytes'],'archive_sha256':sha(archive),'archive_members':len(members),
 'manifest_files_verified':len(manifest),'protocol_sha256':sha(ROOT/'protocol/board_v2.json'),'hardware_image_forwards_supported':103,
 'formal_samples_verified':96,'warmup_measurement_records':6,'probe_samples_verified':1,'raw_arrays_verified':97,'decoded_all_class_rows':decoded,
 'fixed_E010_raw_repeats_exact':60,'probe_vs_formal_same_photo_exact':True,'prior_interrupted192_raw_arrays_exact':old_compare,
 'maximum_independent_statistics_delta':max_stats_delta,'profiles':cases,'final_known_O8_bit_sha256':state['PL_after_bit_sha256'],
 'three_sizes_same_engine_control':False,'actual_camera_or_highres_capture_measured':False,'background_identity_active':False,
 'current_cow_finetuned_weights_deployed':False,'cow_count_accuracy_admitted':False,'joint_foreground_background_5FPS_proven':False,
 'whole_goal_complete':False}
save(ROOT/'results/independent_profile_verification.json',result)
with (ROOT/'results/all_profile_samples.csv').open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({k:v for k,v in result.items() if k not in ['profiles']}))
for r in cases:print(json.dumps(r))
