"""Independent pixel/causality/score audit of the actual video-chain artifact."""
from pathlib import Path
from collections import defaultdict,Counter
from PIL import Image,ImageOps,ImageDraw
import csv,hashlib,json,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
record=json.loads((ROOT/'results/bundle_record.json').read_text());bundle=ROOT/'results/video_chain_delivery.tar.gz'
assert bundle.stat().st_size==record['bytes'] and hashlib.sha256(bundle.read_bytes()).hexdigest()==record['sha256']
dest=ROOT/'delivery'
if not dest.exists():
    dest.mkdir()
    with tarfile.open(bundle) as tf:tf.extractall(dest,filter='data')
files=json.loads((dest/'delivery_manifest.json').read_text())
for row in files:
    path=(dest/row['path']).resolve();assert path.is_relative_to(dest.resolve())
    assert path.stat().st_size==row['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
for relative in ['tools/run_video_chain.py','tools/identity_worker.py','tools/snapshot_bank.py','tools/verify_actual_worker.py','protocol/video_chain_v1.json']:
    assert hashlib.sha256((ROOT/relative).read_bytes()).digest()==hashlib.sha256((dest/relative).read_bytes()).digest()
replay=dest/'results/replay';summary=json.loads((replay/'summary.json').read_text());events=json.loads((replay/'events.json').read_text())
protocol=json.loads((dest/'protocol/video_chain_v1.json').read_text());frames=list(csv.DictReader((replay/'frames.csv').open()))
source_verification=json.loads((dest/'results/verification/summary.json').read_text())
assert source_verification['status']=='PASS' and len(source_verification['native_photo_source_frame_checks'])==len(events)==7
assert len(source_verification['true_repeated_query_forwards'])==35 and source_verification['positive_gallery_self_query_all_conditions_passed']
assert summary['source_frames_decoded']==14008 and len(frames)==2802 and [int(r['source_frame']) for r in frames]==list(range(0,14008,5))
assert summary['parent_pid']!=summary['worker_pid'] and summary['worker_ready']['device']=='cpu' and summary['worker_exitcode']==0
assert all(int(r['retained_snapshot_bytes'])<=33554432 for r in frames)
qualities=0;model_queries=0;old_source=ROOT.parent/'identity_training_20261026/delivery/results/study'
old_index=json.loads((old_source/'feature_index.json').read_text())['evaluation_gallery']
labels=sorted({r['identity'] for r in old_index});rows=[]
for event in events:
    selected=event['selected_snapshot'];candidates=event['candidate_quality_records'];best=sorted(candidates,key=lambda r:(-r['quality'],r['source_frame']))[0]
    assert selected['source_frame']==best['source_frame'] and selected['quality']==best['quality']
    assert all(0<=event['source_time_s']-r['source_time_s']<=2.00000001 and r['source_frame']<=event['source_frame'] for r in candidates)
    assert event['rf_observation_horizon_source_s']>=event['source_time_s']+.5
    assert event['status'] not in ['QUEUED','PENDING_RF_WINDOW']
    for candidate in candidates:
        with Image.open(replay/candidate['quality_png_path']) as im:gray=np.array(im.convert('L'),dtype=float)
        padded=np.pad(gray,1,mode='reflect')
        lap=padded[1:-1,:-2]+padded[1:-1,2:]+padded[:-2,1:-1]+padded[2:,1:-1]-4*gray
        assert abs(float(lap.var())-candidate['quality'])<1e-8;qualities+=1
    with Image.open(replay/selected['native_photo_path']) as im:
        native=im.convert('RGB');assert native.size==(2560,1440)
        native_crop=native.crop(tuple(selected['box']))
    with Image.open(replay/selected['crop_path']) as im:assert np.array_equal(np.array(im.convert('RGB')),np.array(native_crop))
    rotation=Image.Transpose.ROTATE_90 if event['direction']=='A->B' else Image.Transpose.ROTATE_270
    expected=native_crop.transpose(rotation)
    with Image.open(replay/selected['oriented_crop_path']) as im:assert np.array_equal(np.array(im.convert('RGB')),np.array(expected))
    assert min(native_crop.size)>=128 and selected['crop_size']==list(native_crop.size)
    result=event['worker_result'];assert result['worker_pid']==summary['worker_pid'] and result['status']=='COMPLETED'
    assert event['enqueue_wall_ns']<=result['started_wall_ns']<=result['finished_wall_ns']<=event['deadline_wall_ns']
    assert selected['decoded_wall_ns']<=event['observed_wall_ns']<=event['capture_saved_wall_ns']<=event['enqueue_wall_ns']
    assert result['finished_wall_ns']<=summary['frontend_eof_wall_ns']
    assert len(result['conditions'])==5
    for condition in result['conditions']:
        # The gallery was previously stored on GPU; allow the measured CPU/GPU
        # float32 tolerance. A second real CPU forward is verified separately.
        vectors=np.load(old_source/condition['condition']/'evaluation_embeddings.npz')['gallery'].astype(float)
        query=np.array(condition['feature_vector'],dtype=float);assert abs(np.linalg.norm(query)-1)<1e-5
        values=vectors@query
        scores=[max(values[i] for i,r in enumerate(old_index) if r['identity']==label) for label in labels]
        best_index=int(np.argmax(scores));assert labels[best_index]==condition['candidate_anonymous_id']
        assert abs(float(scores[best_index])-condition['cosine_similarity'])<2e-5
        assert condition['passes_frozen_threshold']==(condition['cosine_similarity']>=condition['frozen_threshold'])
        assert condition['verified_identity'] is False;model_queries+=1
    rows.append({'event_id':event['event_id'],'source_time_s':event['source_time_s'],'photo_frame':selected['source_frame'],
                 'native_crop_size':selected['crop_size'],'worker_service_ms':(result['finished_wall_ns']-result['started_wall_ns'])/1e6,
                 'queue_wait_ms':(result['started_wall_ns']-event['enqueue_wall_ns'])/1e6,'source_photo_to_candidate_host_ms':(result['finished_wall_ns']-selected['decoded_wall_ns'])/1e6})
journal=[json.loads(line) for line in (replay/'events.jsonl').read_text().splitlines()]
for event in events:
    transitions=[r['transition'] for r in journal if r['event_id']==event['event_id']]
    assert transitions==['EVENT_OBSERVED','SNAPSHOT_SAVED','QUEUED',event['status']]
old=json.loads((ROOT.parent/'data_audit_20261026/server_results/delivery/evidence/multicam_finetuned_summary.json').read_text())
assert summary['A_to_B']==old['A_to_B']==7 and summary['B_to_A']==old['B_to_A']==0
sheet=Image.new('RGB',(960,7*205),'white');draw=ImageDraw.Draw(sheet)
for i,event in enumerate(events):
    selected=event['selected_snapshot']
    with Image.open(replay/selected['native_photo_path']) as im:sheet.paste(ImageOps.contain(im.convert('RGB'),(475,175)),(0,i*205+25))
    with Image.open(replay/selected['oriented_crop_path']) as im:sheet.paste(ImageOps.contain(im.convert('RGB'),(475,175)),(480,i*205+25))
    draw.text((4,i*205+4),f'event{i+1} t={event["source_time_s"]:.1f}s native 2560x1440; frame {selected["source_frame"]}',fill='black')
    draw.text((484,i*205+4),f'Actual crop after orientation; all five reject, ID unverified',fill='black')
sheet.save(ROOT/'results/native_capture_contact.jpg',quality=92)
report={'status':'PASS','bundle_sha256':record['sha256'],'manifest_files_verified':len(files),'decoded_source_prefix_frames':14008,
        'detection_frames':2802,'native_photos':len(events),'exact_source_photo_checks':len(source_verification['native_photo_source_frame_checks']),
        'independent_quality_variance_checks':qualities,'actual_query_outputs_independently_scored':model_queries,
        'repeated_real_model_forwards_verified':len(source_verification['true_repeated_query_forwards']),
        'positive_self_match_control':'PASS_FOR_INTERFACE_ONLY','all_event_terminal_statuses':dict(Counter(e['status'] for e in events)),
        'online_host_interval_overlap_jobs':summary['jobs_overlapping_foreground_host_intervals'],'post_eof_completed_jobs':0,
        'unchanged_development_event_count':True,'per_event_host_timings':rows,
        'identity_accuracy_verified':False,'pynq_measured':False,'scope':'Source pixels, crop/rotation, causal selection, lifecycle, real CPU model replay and gallery arithmetic; no raw-video identity labels'}
(ROOT/'results/independent_verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
