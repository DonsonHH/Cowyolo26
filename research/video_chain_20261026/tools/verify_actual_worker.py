"""Source-pixel, native-photo and true model-forward replay with positive control."""
from pathlib import Path
import hashlib,json,multiprocessing,os,queue,time
from identity_worker import worker_main
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'video_chain'
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    import cv2,numpy as np
    OUT=ROOT/'results/verification';OUT.mkdir(parents=True,exist_ok=False)
    replay=ROOT/'results/replay';p=json.loads((ROOT/'protocol/video_chain_v1.json').read_text());events=json.loads((replay/'events.json').read_text())
    cv2.setNumThreads(1);source=PROJECT/p['source_video'];assert sha(source.read_bytes())==p['source_video_sha256']
    cap=cv2.VideoCapture(str(source));photo_checks=[];quality_checks=[]
    frame_cache={}
    for event in events:
        for record in event['candidate_quality_records']:
            frame=record['source_frame']
            if frame not in frame_cache:
                assert cap.set(cv2.CAP_PROP_POS_FRAMES,frame)
                ok,image=cap.read();assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES))==frame+1
                frame_cache[frame]=image
            image=frame_cache[frame];x1,y1,x2,y2=record['box']
            gray=cv2.cvtColor(image[y1:y2,x1:x2],cv2.COLOR_BGR2GRAY)
            resized=cv2.resize(gray,(max(1,round((x2-x1)*128/(y2-y1))),128),interpolation=cv2.INTER_AREA)
            actual=cv2.Laplacian(resized,cv2.CV_64F).var()
            encoded=cv2.imdecode(np.frombuffer((replay/record['quality_png_path']).read_bytes(),dtype=np.uint8),cv2.IMREAD_GRAYSCALE)
            assert np.array_equal(encoded,resized) and abs(actual-record['quality'])<1e-9
            quality_checks.append({'event_id':event['event_id'],'source_frame':frame,'original_source_pixels_equal_quality_thumbnail':True})
        record=event['selected_snapshot'];image=frame_cache[record['source_frame']]
        ok,encoded=cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,95]);assert ok
        assert sha(encoded.tobytes())==record['native_photo_sha256']
        photo_checks.append({'event_id':event['event_id'],'source_frame':record['source_frame'],'native_jpeg_reencoding_exact_sha256_equality':True})
    cap.release();frame_cache.clear()
    ctx=multiprocessing.get_context('spawn');tasks=ctx.Queue(4);results=ctx.Queue(16)
    worker=ctx.Process(target=worker_main,args=(tasks,results,p,str(PROJECT)));worker.start();ready=results.get(timeout=120);assert ready['kind']=='ready'
    repeated=[]
    try:
        for event in events:
            crop=replay/event['selected_snapshot']['oriented_crop_path']
            tasks.put({'event_id':event['event_id'],'oriented_crop_path':str(crop),'oriented_crop_sha256':sha(crop.read_bytes()),'deadline_wall_ns':time.monotonic_ns()+30_000_000_000})
            result=results.get(timeout=60);assert result['kind']=='result' and result['status']=='COMPLETED',result
            old=event['worker_result']
            for a,b in zip(old['conditions'],result['conditions']):
                assert a['condition']==b['condition'] and a['candidate_anonymous_id']==b['candidate_anonymous_id']
                error=float(np.max(np.abs(np.array(a['feature_vector'])-np.array(b['feature_vector']))))
                assert error<=1e-5 and abs(a['cosine_similarity']-b['cosine_similarity'])<=1e-5
                assert a['passes_frozen_threshold']==b['passes_frozen_threshold']
                repeated.append({'event_id':event['event_id'],'condition':a['condition'],'max_absolute_feature_error':error,'score_and_threshold_decision_agree':True})
        index=json.loads((PROJECT/'identity_training/results/study/feature_index.json').read_text())
        reference=index['evaluation_gallery'][0];file=PROJECT/'identity_training'/reference['relative_path']
        tasks.put({'event_id':'gallery-self-match-positive-control','oriented_crop_path':str(file),'oriented_crop_sha256':sha(file.read_bytes()),'deadline_wall_ns':time.monotonic_ns()+30_000_000_000})
        positive=results.get(timeout=60);assert positive['status']=='COMPLETED'
        assert all(c['candidate_anonymous_id']==reference['identity'] and c['cosine_similarity']>.9999 and c['passes_frozen_threshold'] for c in positive['conditions'])
        tasks.put(None);worker.join(timeout=30);assert worker.exitcode==0
    finally:
        if worker.is_alive():worker.terminate();worker.join(timeout=5)
    (OUT/'positive_control.json').write_text(json.dumps({'scope':'Gallery image queried against itself; interface sanity only, not independent recognition accuracy','expected_anonymous_id':reference['identity'],'result':positive},indent=2))
    summary={'status':'PASS','job_id':os.environ['SLURM_JOB_ID'],'native_photo_source_frame_checks':photo_checks,
             'all_candidate_quality_source_pixel_checks':quality_checks,'true_repeated_query_forwards':repeated,
             'positive_gallery_self_query_all_conditions_passed':True,'source_identity_ground_truth_verified':False,
             'scope':'Actual source-frame JPEG reproducibility, exact quality pixels and repeated model forward/interface verification; identity labels of source video remain unverified'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:(len(v) if isinstance(v,list) else v) for k,v in summary.items()},indent=2),flush=True)
if __name__=='__main__':main()
