from pathlib import Path
from collections import defaultdict
import hashlib,json,os,socket,tarfile,time
import cv2,numpy as np
from geometry_probe import ROOT,load,sha,save,make_template,image_features,compare,rank
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(4)
    p=load(ROOT/'protocol/geometry_v1.json');q=load(ROOT/'protocol/refinement_v1.json')
    assert q['coarse_protocol_sha256']==sha(ROOT/'protocol/geometry_v1.json') and q['source_search_implementation_sha256']==sha(ROOT/'tools/geometry_probe.py')
    assert sha(ROOT/'results/geometry_coarse/top_results.json')==q['coarse_results_sha256']
    assert sha(p['source_video'])==p['source_sha256']
    out=ROOT/'results/geometry_refined';out.mkdir(exist_ok=False);sift=cv2.SIFT_create(**p['SIFT'])
    templates=[];needed=defaultdict(list);top=[[] for _ in q['templates']];metrics=[];frames_seen=[];started=time.perf_counter()
    for t in q['templates']:
        index=t['template_index'];r=t['gallery'];assert sha(r['path'])==r['sha256']
        im=cv2.imread(r['path']);templates.append(make_template(im,r,p,sift))
        for frame in t['refine_frame0s']:needed[frame].append(index)
    cap=cv2.VideoCapture(p['source_video']);assert cap.isOpened()
    try:
        for frame in range(max(needed)+1):
            ok,image=cap.read();assert ok,frame
            if frame not in needed:continue
            points,des=image_features(image,p,sift);frames_seen.append(frame)
            for i in needed[frame]:
                value=compare(templates[i],image,points,des,p);value['source_frame0']=frame
                metrics.append({'template_index':i,**{k:v for k,v in value.items() if k not in ['homography_template_to_native','mapped_native_corners','inlier_template_xy','inlier_native_xy']}})
                top[i]=sorted(top[i]+[value],key=rank,reverse=True)[:p['retained_per_template']]
    finally:cap.release()
    assert frames_seen==q['unique_refinement_frames'] and len(metrics)==q['per_template_comparisons']
    records=[];artifacts=[];cap=cv2.VideoCapture(p['source_video'])
    try:
        for i,t in enumerate(templates):
            row={'template_index':i,'gallery':t['spec'],'top':top[i]};best=top[i][0];frame=best['source_frame0']
            assert cap.set(cv2.CAP_PROP_POS_FRAMES,frame);ok,image=cap.read();assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES))==frame+1
            native=out/f'template{i:02d}_source_f{frame:05d}.jpg';assert cv2.imwrite(str(native),image,[cv2.IMWRITE_JPEG_QUALITY,95])
            item={'template_index':i,'frame0':frame,'native_source':native.relative_to(ROOT).as_posix(),'native_sha256':sha(native)}
            if 'homography_template_to_native' in best:
                H=np.asarray(best['homography_template_to_native'])
                warped=cv2.warpPerspective(image,np.linalg.inv(H),(t['width'],t['height']),flags=cv2.INTER_LINEAR)
                imagefile=out/f'template{i:02d}_source_rewarp.png';assert cv2.imwrite(str(imagefile),warped)
                item.update(rewarp_file=imagefile.relative_to(ROOT).as_posix(),rewarp_sha256=sha(imagefile))
            artifacts.append(item);records.append(row)
    finally:cap.release()
    save(out/'top_results.json',records);save(out/'all_metrics.json',metrics);save(out/'artifacts.json',artifacts)
    summary={'status':'ALL30_TEMPLATES_PREDECLARED_LOCAL_GEOMETRIC_REFINEMENT_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
      'refinement_protocol_sha256':sha(ROOT/'protocol/refinement_v1.json'),'templates':30,'unique_source_frames':len(frames_seen),
      'template_frame_comparisons':len(metrics),'geometry_candidate_templates':sum(r['top'][0]['geometry_pass'] for r in records),
      'best_each':[{'template_index':r['template_index'],'anonymous_ID':r['gallery']['published_anonymous_ID'],'filename':r['gallery']['filename'],
                  **{k:r['top'][0].get(k) for k in ['source_frame0','geometry_pass','NCC','inliers','inlier_fraction','template_inlier_hull_fraction','mean_absolute_BGR_error']}} for r in records],
      'elapsed_s':time.perf_counter()-started,'original_decoded_prefix_frames':max(needed)+1,
      'source_identity_mapping_certified':False,'new_identity_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
    save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    files=[ROOT/'protocol/refinement_v1.json',ROOT/'tools/refine_geometry.py',*[f for f in out.rglob('*') if f.is_file()]]
    manifest=[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]
    save(ROOT/'refined_manifest.json',{'files':manifest});archive=ROOT/'geometry_refined_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for r in manifest:tf.add(ROOT/r['file'],arcname=r['file'])
        tf.add(ROOT/'refined_manifest.json',arcname='refined_manifest.json')
    print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'files':len(manifest)+1}),flush=True)
if __name__=='__main__':main()
