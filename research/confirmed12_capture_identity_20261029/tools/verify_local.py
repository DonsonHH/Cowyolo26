from pathlib import Path,PurePosixPath
from collections import defaultdict,Counter
from PIL import Image
import csv,hashlib,importlib.util,json,math,sys,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
    with p.open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def main():
    record=load(ROOT/'evidence/delivery_record.json');archive=ROOT/'chain_delivery.tar.gz';dest=ROOT/'delivery'
    assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256'] and not dest.exists()
    with tarfile.open(archive,'r:gz') as tf:
        manifest=json.loads(tf.extractfile('delivery_manifest.json').read())['files'];expected={r['file']:r for r in manifest};members=tf.getmembers()
        assert len(manifest)==len(expected)==120 and len(members)==record['files']==121
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            target=dest.joinpath(*name.parts).resolve();assert target.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);assert sha(target)==hashlib.sha256(data).hexdigest()
    p=load(ROOT/'protocol/chain_v1.json');folder=dest/'results/replay';events=load(folder/'events.json');summary=load(folder/'summary.json')
    assert sha(ROOT/'protocol/chain_v1.json')==sha(dest/'protocol/chain_v1.json')==summary['protocol_sha256']
    for name in ['tools/identity_worker.py','tools/run_chain.py','tools/verify_remote.py']:
        assert sha(ROOT/name)==sha(dest/name)
    for name,digest in p['input_module_sha256'].items():assert sha(ROOT/'input'/name)==sha(dest/'input'/name)==digest
    old=load(PROJECT/'video_chain_20261026/protocol/video_chain_v1.json');assert p['identity']==old['identity'] and p['snapshots']==old['snapshots']
    assert sha(ROOT/'input/snapshot_bank.py')==sha(PROJECT/'video_chain_20261026/tools/snapshot_bank.py')
    assert p['expected_events']==[{'time_s':e['source_time_s'],'track_id':e['track_id'],'direction':e['direction'],'frame0':e['frame0']} for e in events]
    assert len(events)==summary['event_count']==summary['native_photos']==summary['worker_completed_jobs']==12
    assert sha(ROOT/'evidence/events_initial_inspection.json')==sha(folder/'events.json')
    cache=PROJECT/'firststage_iou_regression_20261029/delivery/results/original_seed26__original_fused'
    observations=load(cache/'observations.json')
    sys.path.insert(0,str(PROJECT/'long_video_fixed_replay_20261029/input'))
    spec=importlib.util.spec_from_file_location('independent_source_counter',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py')
    scanner=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanner)
    calculated,accepted=scanner.batch_events(observations,True);assert calculated==p['expected_events']
    candidates=read(folder/'snapshot_candidate_inputs.csv');by_frame=defaultdict(list)
    for r in candidates:
        by_frame[int(r['frame0'])].append({'frame0':int(r['frame0']),'track_id':int(r['track_id']),
            'box':[int(r[k]) for k in ['box_x1','box_y1','box_x2','box_y2']],
            'quality':float(r['quality']),'confidence':float(r['confidence']),'accepted':r['consider_result']=='True'})
    by_event=defaultdict(list)
    for e in events:by_event[e['frame0']].append(e)
    banks={};snapshot_rows=0
    assert summary['snapshot_bank_evictions']==0
    for frame in range(0,10874,5):
        banks={tid:[c for c in values if frame/25-c['frame0']/25<=2] for tid,values in banks.items()}
        banks={tid:values for tid,values in banks.items() if values}
        for row in by_frame[frame]:
            tid=row['track_id'];old=banks.get(tid,[]);proposed=sorted(old+[row],key=lambda c:(-c['quality'],c['frame0']))[:3]
            assert row['accepted']==(row in proposed)
            if row in proposed:banks[tid]=proposed
            assert len(banks)<=32
        for event in by_event[frame]:
            chosen=banks.pop(event['track_id'],[]);actual=event['quality_candidates'];assert len(chosen)==len(actual)==3
            for candidate,stored in zip(chosen,actual):
                assert candidate['frame0']==stored['frame0'] and candidate['box']==stored['box'] and candidate['quality']==stored['quality']
                assert 8912<=stored['frame0']<=frame and frame/25-stored['source_time_s']<=2
                path=folder/stored['quality_path'];assert sha(path)==stored['quality_sha256']
                with Image.open(path) as im:array=np.asarray(im,dtype=np.float64)
                padded=np.pad(array,1,mode='reflect')
                lap=padded[1:-1,:-2]+padded[1:-1,2:]+padded[:-2,1:-1]+padded[2:,1:-1]-4*array
                assert abs(float(np.var(lap))-stored['quality'])<1e-9;snapshot_rows+=1
    bank_numbers=[int(r['bank_bytes_after_consider']) for r in candidates]+[int(r['retained_bank_bytes']) for r in read(folder/'frontend_ticks.csv')]
    assert max(bank_numbers)==summary['snapshot_bank_peak_bytes']<=summary['snapshot_bank_byte_limit']==33554432
    gallery=load(folder/'gallery_vectors.json');labels=gallery['labels'];index=gallery['entries']
    assert index==load(ROOT/'input/gallery_source_index.json') and len(index)==30 and len(labels)==6
    assert gallery['models_and_thresholds']==p['identity']['conditions']
    score_count=0;image_dotproducts=0;raster=[];terminals=Counter();condition_pass=Counter();case_rows=[]
    transitions=[json.loads(line) for line in (folder/'transitions.jsonl').read_text().splitlines()];by_transition=defaultdict(list)
    for r in transitions:by_transition[r['event_id']].append(r)
    for event in events:
        s=event['selected_snapshot'];assert s['frame0']==event['quality_candidates'][0]['frame0']
        for a,b in [('native_path','native_sha256'),('crop_path','crop_sha256'),('oriented_path','oriented_sha256')]:
            path=folder/s[a];assert sha(path)==s[b]
            with Image.open(path) as im:im.verify()
            raster.append({'path':str(path.resolve()),'sha256':sha(path)})
        with Image.open(folder/s['native_path']) as im:
            native=im.convert('RGB');assert native.size==(2560,1440);crop=np.asarray(native.crop(s['box']))
        with Image.open(folder/s['crop_path']) as im:assert np.array_equal(np.asarray(im.convert('RGB')),crop)
        with Image.open(folder/s['oriented_path']) as im:assert np.array_equal(np.asarray(im.convert('RGB')),np.rot90(crop,k=1 if s['rotation_CCW_degrees']==90 else 3))
        assert len(event['quality_candidates'])==3
        for q in event['quality_candidates']:
            path=folder/q['quality_path'];raster.append({'path':str(path.resolve()),'sha256':sha(path)})
        assert event['rf_status']=='EXPLICIT_MOCK_MISSING_NO_READER'
        expected_closed=math.ceil((event['frame0']+.5*25)/5)*5
        assert event['rf_closed_frame0']==expected_closed and event['rf_closed_source_time_s']==expected_closed/25
        result=event['worker_result'];assert result['status']=='COMPLETED' and result['event_id']==event['event_id']
        assert s['decoded_wall_ns']<=event['event_observed_wall_ns']<=event['snapshot_saved_wall_ns']<=event['enqueue_wall_ns']<=result['started_wall_ns']<=result['finished_wall_ns']<=result['parent_received_wall_ns']
        assert result['finished_wall_ns']<=event['deadline_wall_ns'] and result['finished_wall_ns']<summary['frontend_EOF_wall_ns']
        assert result['worker_pid']==summary['worker_pid']!=summary['parent_pid']
        assert event['verified_identity'] is False and event['source_identity_reference'] is None
        assert load(folder/'events'/(event['event_id']+'.json'))==event
        steps=by_transition[event['event_id']]
        assert [r['transition'] for r in steps]==['EVENT_OBSERVED','SNAPSHOT_SAVED','QUEUED',event['status']]
        assert [r['wall_ns'] for r in steps]==sorted(r['wall_ns'] for r in steps)
        passing=[]
        for c,configuration in zip(result['conditions'],p['identity']['conditions']):
            name=c['condition'];assert name==configuration['name'] and c['model_sha256']==configuration['checkpoint_sha256'] and c['frozen_threshold']==configuration['threshold']
            vector=np.asarray(c['feature_vector'],float);g=np.asarray(gallery['conditions'][name]['features'],float)
            scores=np.asarray([sum(a*b for a,b in zip(row,vector)) for row in g]);assert np.max(np.abs(scores-np.asarray(c['gallery_image_cosines'])))<1e-12
            aggregated=[max(float(scores[i]) for i,r in enumerate(index) if r['identity']==label) for label in labels]
            expected_scores=[{'anonymous_id':label,'score':score} for label,score in zip(labels,aggregated)]
            assert all(abs(a['score']-b['score'])<1e-12 and a['anonymous_id']==b['anonymous_id'] for a,b in zip(expected_scores,c['identity_scores']))
            best=max(range(len(labels)),key=lambda i:aggregated[i]);assert labels[best]==c['candidate_anonymous_id'] and abs(aggregated[best]-c['cosine_similarity'])<1e-12
            assert c['passes_frozen_threshold']==(aggregated[best]>=configuration['threshold']) and c['verified_identity'] is False
            assert c['query_tensor_shape']==[1,3,224,224] and len(c['query_tensor_sha256'])==64
            assert abs(np.linalg.norm(vector)-1)<1e-5;score_count+=1;image_dotproducts+=len(scores)
            if c['passes_frozen_threshold']:condition_pass[name]+=1;passing.append({'condition':name,'candidate_anonymous_id':c['candidate_anonymous_id'],
                'similarity':c['cosine_similarity'],'threshold':c['frozen_threshold'],'margin_over_threshold':c['cosine_similarity']-c['frozen_threshold']})
        expected_status='CANDIDATE_THRESHOLD_PASSED_UNVERIFIED' if passing else 'ALL_CONDITIONS_REJECTED'
        assert event['status']==expected_status;terminals[expected_status]+=1
        case_rows.append({'event_id':event['event_id'],'frame0':event['frame0'],'snapshot_frame0':s['frame0'],'passing_conditions':passing,
                          'state':expected_status,'verified_identity':False,'crop_source_identity_accuracy':None})
    assert len(raster)==72 and snapshot_rows==36 and score_count==60 and image_dotproducts==1800
    assert dict(terminals)==summary['task_terminal_status_counts'] and terminals['ALL_CONDITIONS_REJECTED']==10 and terminals['CANDIDATE_THRESHOLD_PASSED_UNVERIFIED']==2
    assert {c['name']:condition_pass[c['name']] for c in p['identity']['conditions']}==summary['threshold_pass_counts_by_condition']
    verified=load(dest/'results/verification/summary.json');assert len(verified['photo_checks'])==12 and len(verified['quality_checks'])==36 and len(verified['repeated_real_queries'])==60
    positive=load(dest/'results/verification/positive_control.json');assert len(positive['result']['conditions'])==5
    assert all(c['passes_frozen_threshold'] and c['candidate_anonymous_id']==positive['expected_anonymous_id'] for c in positive['result']['conditions'])
    report={'status':'12_EVENT_PHOTOS_36_SNAPSHOT_CHOICES_60_IDENTITY_DECISIONS_AND_LIFECYCLES_INDEPENDENTLY_VERIFIED',
            'manifest_files':120,'archive_members':121,'events':12,'counter_ticks_recomputed':2175,'snapshot_consider_inputs':len(candidates),
            'selected_candidate_quality_source_checks':36,'native_photos':12,'raster_files_verified':72,
            'model_query_results':60,'image_cosine_dotproducts_verified':1800,'per_identity_scores_verified':360,
            'real_fresh_process_repeated_queries':60,'gallery_self_query_controls':5,'total_query_forward_calls_including_repeats_and_control':125,
            'terminal_status_counts':dict(terminals),'passing_cases':case_rows,'retained_snapshot_peak_bytes':summary['snapshot_bank_peak_bytes'],
            'all_worker_jobs_finished_before_frontend_EOF':True,'verified_source_cow_identities':0,'source_identity_accuracy':None,
            'new_detector_forwards':0,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False,'rasters':raster}
    target=ROOT/'results/independent_verification.json';assert not target.exists();target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['passing_cases','rasters']}))
if __name__=='__main__':main()
