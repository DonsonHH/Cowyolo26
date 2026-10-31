"""Independent source decode, repeated CPU model queries and interface control."""
from pathlib import Path
import hashlib,json,multiprocessing,os,queue,socket,sys,time,tarfile
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/confirmed12_capture_identity_20261029');PROJECT=ROOT.parent
from identity_worker import worker_main
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):assert not p.exists(),p;p.write_text(json.dumps(value,indent=2)+'\n')
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    import cv2,numpy as np
    from PIL import Image
    cv2.setNumThreads(1);p=load(ROOT/'protocol/chain_v1.json');replay=ROOT/'results/replay'
    summary=load(replay/'summary.json');events=load(replay/'events.json')
    assert summary['event_count']==summary['native_photos']==summary['worker_completed_jobs']==12 and summary['true_query_forwards']==60
    assert summary['protocol_sha256']==sha(ROOT/'protocol/chain_v1.json')
    assert sha(ROOT/'tools/identity_worker.py')==p['identity_worker_sha256'] and sha(p['source_video'])==p['source_video_sha256']
    out=ROOT/'results/verification';out.mkdir(exist_ok=False)
    cap=cv2.VideoCapture(p['source_video']);assert cap.isOpened();frame_cache={};qualities=[];photos=[]
    try:
        for event in events:
            assert len(event['quality_candidates'])<=3
            for choice in event['quality_candidates']:
                frame=choice['frame0']
                if frame not in frame_cache:
                    assert cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,image=cap.read();assert ok
                    assert round(cap.get(cv2.CAP_PROP_POS_FRAMES))==frame+1;frame_cache[frame]=image
                image=frame_cache[frame];x1,y1,x2,y2=choice['box']
                native=cv2.cvtColor(image[y1:y2,x1:x2],cv2.COLOR_BGR2GRAY)
                thumb=cv2.resize(native,(max(1,round((x2-x1)*128/(y2-y1))),128),interpolation=cv2.INTER_AREA)
                saved=cv2.imdecode(np.frombuffer((replay/choice['quality_path']).read_bytes(),np.uint8),cv2.IMREAD_GRAYSCALE)
                assert np.array_equal(thumb,saved) and abs(float(cv2.Laplacian(thumb,cv2.CV_64F).var())-choice['quality'])<1e-9
                qualities.append({'event_id':event['event_id'],'frame0':frame,'quality_pixels_and_value_match_source':True})
            selected=event['selected_snapshot'];image=frame_cache[selected['frame0']]
            valid,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,95]);assert valid
            assert hashlib.sha256(encoded.tobytes()).hexdigest()==selected['native_sha256']
            photos.append({'event_id':event['event_id'],'frame0':selected['frame0'],'source_reencoded_JPEG_sha256_exact':True})
    finally:cap.release();frame_cache.clear()
    ctx=multiprocessing.get_context('spawn');tasks=ctx.Queue(4);results=ctx.Queue(16)
    protocol={**p,'identity_gallery_export_path':str(out/'gallery_vectors.json')}
    worker=ctx.Process(target=worker_main,args=(tasks,results,protocol,str(PROJECT)));worker.start();repeated=[]
    try:
        ready=results.get(timeout=120);assert ready['kind']=='ready' and ready['device']=='cpu'
        old_gallery=load(replay/'gallery_vectors.json');new_gallery=load(out/'gallery_vectors.json')
        assert old_gallery['entries']==new_gallery['entries'] and old_gallery['models_and_thresholds']==new_gallery['models_and_thresholds']
        gallery_errors={}
        for name,old in old_gallery['conditions'].items():
            error=float(np.max(np.abs(np.asarray(old['features'])-np.asarray(new_gallery['conditions'][name]['features']))))
            assert error<=1e-5;gallery_errors[name]=error
        for event in events:
            selected=event['selected_snapshot'];file=replay/selected['oriented_path']
            tasks.put({'event_id':event['event_id'],'oriented_crop_path':str(file),'oriented_crop_sha256':sha(file),
                       'deadline_wall_ns':time.monotonic_ns()+30_000_000_000})
            result=results.get(timeout=60);assert result['kind']=='result' and result['status']=='COMPLETED',result
            old=event['worker_result'];assert len(old['conditions'])==len(result['conditions'])==5
            for a,b in zip(old['conditions'],result['conditions']):
                assert a['condition']==b['condition'] and a['model_sha256']==b['model_sha256']
                assert a['candidate_anonymous_id']==b['candidate_anonymous_id'] and a['passes_frozen_threshold']==b['passes_frozen_threshold']
                assert a['frozen_threshold']==b['frozen_threshold'] and a['query_tensor_sha256']==b['query_tensor_sha256']
                difference=float(np.max(np.abs(np.asarray(a['feature_vector'])-np.asarray(b['feature_vector']))))
                assert difference<=1e-5 and abs(a['cosine_similarity']-b['cosine_similarity'])<=1e-5
                repeated.append({'event_id':event['event_id'],'condition':a['condition'],'feature_max_difference':difference,
                                 'candidate_score_and_threshold_agree':True,'input_tensor_sha256_same':True})
            save(out/(event['event_id']+'_repeated.json'),result)
        first=new_gallery['entries'][0];file=PROJECT/'identity_training'/first['relative_path']
        tasks.put({'event_id':'INTERFACE_GALLERY_SELF_MATCH','oriented_crop_path':str(file),'oriented_crop_sha256':sha(file),
                   'deadline_wall_ns':time.monotonic_ns()+30_000_000_000})
        positive=results.get(timeout=60);assert positive['status']=='COMPLETED'
        assert all(c['candidate_anonymous_id']==first['identity'] and c['cosine_similarity']>.9999 and c['passes_frozen_threshold'] for c in positive['conditions'])
        save(out/'positive_control.json',{'scope':'Gallery image queried against itself; interface sanity, not independent identity accuracy.',
            'expected_anonymous_id':first['identity'],'result':positive})
        tasks.put(None);worker.join(timeout=30);assert worker.exitcode==0
    finally:
        if worker.is_alive():worker.terminate();worker.join(timeout=5)
    result={'status':'12_NATIVE_PHOTOS_SOURCE_MATCH_AND60_REAL_QUERIES_REPEATED_WITH_INTERFACE_POSITIVE_CONTROL',
            'job_id':os.environ['SLURM_JOB_ID'],'photo_checks':photos,'quality_checks':qualities,
            'repeated_real_queries':repeated,'gallery_feature_max_errors':gallery_errors,
            'positive_self_query_conditions':5,'source_identity_accuracy_proven':False,'new_detector_forwards':0,'new_training_updates':0,
            'FPGA_execution_verified':False,'whole_goal_complete':False}
    assert len(photos)==12 and len(repeated)==60;save(out/'summary.json',result)
    print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in result.items()}),flush=True)
    files=[]
    for folder in ['results','input','protocol','tools']:
        for file in sorted((ROOT/folder).rglob('*')):
            if file.is_file():files.append({'file':file.relative_to(ROOT).as_posix(),'bytes':file.stat().st_size,'sha256':sha(file)})
    save(ROOT/'delivery_manifest.json',{'files':files});archive=ROOT/'chain_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for r in files:tf.add(ROOT/r['file'],arcname=r['file'])
        tf.add(ROOT/'delivery_manifest.json',arcname='delivery_manifest.json')
    print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'files':len(files)+1}),flush=True)
if __name__=='__main__':main()
