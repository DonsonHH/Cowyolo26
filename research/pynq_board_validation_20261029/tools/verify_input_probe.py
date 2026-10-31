from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile,statistics
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pixelsha(p):return hashlib.sha256(p.tobytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
transfer=load(ROOT/'evidence/input_probe_transfer.json');archive=ROOT/'input_probe_complete.tar.gz'
assert archive.stat().st_size==transfer['bytes'] and sha(archive)==transfer['sha256']
out=ROOT/'input_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==transfer['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        p=(out/member.name).resolve();assert p.is_relative_to(out.resolve()) and not p.exists()
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(tar.extractfile(member).read())
manifest=load(out/'input_probe_manifest.json');assert len(manifest)==transfer['manifest_files']
for r in manifest:
    p=out/r['relative_file'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
assert sha(out/'input_gate.json')==sha(ROOT/'protocol/input_gate_v1.json') and sha(out/'board_input_probe.py')==sha(ROOT/'tools/board_input_probe.py')
summary=load(out/'input_probe/summary.json');assert sha(out/'input_probe/summary.json')==load(out/'input_probe/terminal.json')['summary_sha256']
events=load(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/events.json');replay=PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay'
cropchecks=0;arrays=0;different=0;diff_channels=0;maximum=0;timing={name:[] for name in ['np_rot90_copy_native_baseline','cv2_rotate_native','cv2_resize_before_rotate']}
for i,row in enumerate(summary['rows']):
    event=next(e for e in events if e['event_id']==row['query_id']);snapshot=event['selected_snapshot'];file=replay/snapshot['native_path']
    assert sha(file)==snapshot['native_sha256']==row['source_photo_sha256'] and row==load(out/'input_probe'/('photo_'+str(i).zfill(2)+'.json'))
    with Image.open(file) as image:native=np.ascontiguousarray(np.asarray(image.convert('RGB'))[:,:,::-1])
    assert native.shape==(1440,2560,3) and pixelsha(native)==row['native_source_BGR_sha256']
    rotated=np.ascontiguousarray(native.transpose(1,0,2)[:,::-1]);assert pixelsha(rotated)==row['native_rotated_BGR_sha256']
    assert row['native_cv2_rotate_pixel_exact'] is True;cropchecks+=1
    for condition in row['size_conditions']:
        size=condition['size'];file=out/'input_probe'/condition['array_file'];assert sha(file)==condition['array_file_sha256']
        with np.load(file) as ar:reference=ar['reference_BGR'];cvnative=ar['cv2native_BGR'];first=ar['resizefirst_BGR']
        assert reference.shape==cvnative.shape==first.shape==(size,size,3) and reference.dtype==cvnative.dtype==first.dtype==np.uint8
        assert pixelsha(reference)==condition['reference_BGR_sha256'] and pixelsha(cvnative)==condition['cv2native_BGR_sha256'] and pixelsha(first)==condition['resizefirst_BGR_sha256']
        assert np.array_equal(reference,cvnative) and condition['native_rotate_letterbox_exact'] is True
        delta=np.abs(reference.astype(np.int16)-first.astype(np.int16));is_equal=bool(np.array_equal(reference,first))
        assert is_equal==condition['resizefirst_letterbox_exact'] and int(np.count_nonzero(delta))==condition['resizefirst_different_channels'] and int(delta.max())==condition['resizefirst_maximum_uint8_delta']
        arrays+=3;different+=not is_equal;diff_channels+=int(np.count_nonzero(delta));maximum=max(maximum,int(delta.max()))
        for name,values in condition['timing_ms'].items():assert len(values)==3 and all(v>0 for v in values);timing[name].extend(values)
assert cropchecks==12 and arrays==108 and len(summary['rows'])==12
assert summary['timed_rule_photo_size_repeats']==sum(len(a) for a in timing.values())==324
assert summary['native_cv2_rotation_exact_all12'] is True and summary['cv2native_letterbox_exact_all36'] is True
assert summary['resizefirst_letterbox_exact_all36'] is (different==0)
result={'status':'12_INDEPENDENT_PIL_DECODE_AND_TRANSPOSE36_INPUT_CONDITIONS108_ARRAYS_AND324_TIMINGS_VERIFIED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'archive_sha256':sha(archive),'archive_members':len(members),
 'native_source_photos_independently_decoded':12,'native_cv2_rotation_vs_independent_transpose_exact':True,
 'letterbox_conditions':36,'saved_arrays_verified':108,'native_cv2_letterbox_exact_conditions':36,
 'resize_first_different_conditions':different,'resize_first_total_different_uint8_channels':diff_channels,
 'resize_first_maximum_uint8_difference':maximum,'resize_first_adopted_as_identical_input':False,
 'timing':{k:{'samples':len(v),'mean_ms':statistics.mean(v),'median_ms':statistics.median(v),'maximum_ms':max(v)} for k,v in timing.items()},
 'new_network_forwards':0,'actual_camera_measurement':False,'whole_goal_complete':False}
save(ROOT/'results/independent_input_verification.json',result);print(json.dumps(result))
