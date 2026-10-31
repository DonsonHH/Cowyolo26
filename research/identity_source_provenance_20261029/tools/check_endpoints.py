from pathlib import Path
import os,socket,json,tarfile
import cv2,numpy as np
from geometry_probe import ROOT,load,sha,save,make_template,image_features,compare
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(2)
    p=load(ROOT/'protocol/geometry_v1.json');q=load(ROOT/'protocol/endpoint_v1.json')
    assert q['source_protocol_sha256']==sha(ROOT/'protocol/geometry_v1.json')
    assert q['source_refinement_results_sha256']==sha(ROOT/'results/geometry_refined/top_results.json')
    out=ROOT/'results/endpoint_check';out.mkdir(exist_ok=False);sift=cv2.SIFT_create(**p['SIFT']);cap=cv2.VideoCapture(p['source_video']);assert cap.isOpened()
    rows=[]
    try:
        for item in q['endpoints']:
            frame=item['predicted_source_frame0'];assert cap.set(cv2.CAP_PROP_POS_FRAMES,frame)
            ok,native=cap.read();assert ok and round(cap.get(cv2.CAP_PROP_POS_FRAMES))==frame+1
            assert sha(item['gallery']['path'])==item['gallery']['sha256'];template_image=cv2.imread(item['gallery']['path'])
            template=make_template(template_image,item['gallery'],p,sift);points,des=image_features(native,p,sift);result=compare(template,native,points,des,p)
            native_path=out/f'template{item["template_index"]:02d}_source_f{frame:05d}.jpg';assert cv2.imwrite(str(native_path),native,[cv2.IMWRITE_JPEG_QUALITY,95])
            row={**item,'match':result,'native_source_file':native_path.relative_to(ROOT).as_posix(),'native_source_sha256':sha(native_path)}
            if 'homography_template_to_native' in result:
                h,w=template_image.shape[:2];H=np.asarray(result['homography_template_to_native'])
                warped=cv2.warpPerspective(native,np.linalg.inv(H),(w,h),flags=cv2.INTER_LINEAR)
                path=out/f'template{item["template_index"]:02d}_diagnostic_rewarp.png';assert cv2.imwrite(str(path),warped)
                mask=np.zeros((h,w),bool);m=.08;mask[round(h*m):round(h*(1-m)),round(w*m):round(w*(1-m))]=True
                mask&=~((template_image[:,:,0]>160)&(template_image[:,:,1]<130)&(template_image[:,:,2]<130))
                a=cv2.cvtColor(template_image,cv2.COLOR_BGR2GRAY)[mask].astype(float);b=cv2.cvtColor(warped,cv2.COLOR_BGR2GRAY)[mask].astype(float)
                row['diagnostic_photometric']={'NCC':float(np.corrcoef(a,b)[0,1]),
                    'mean_absolute_BGR_error':float(np.mean(abs(template_image.astype(float)[mask]-warped.astype(float)[mask]))),
                    'used_despite_geometry_rejection':not result['geometry_pass'],'geometry_pass_not_overridden':True}
                row.update(rewarp_file=path.relative_to(ROOT).as_posix(),rewarp_sha256=sha(path))
            rows.append(row)
    finally:cap.release()
    summary={'status':'TWO_PUBLISHED_ID009_SEQUENCE_ENDPOINTS_CHECKED_WITH_ORIGINAL_GEOMETRY_FILTERS',
      'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/endpoint_v1.json'),'endpoint_results':rows,
      'post_search_development_hypothesis':True,'identity_mapping_certified':False,'new_identity_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
    save(out/'summary.json',summary)
    print(json.dumps({'status':summary['status'],'endpoints':[{'template_index':r['template_index'],'source_frame0':r['predicted_source_frame0'],
          'geometry_pass':r['match']['geometry_pass'],'NCC':r['match'].get('NCC'),'diagnostic_photometric':r.get('diagnostic_photometric')} for r in rows]}),flush=True)
    files=[ROOT/'protocol/endpoint_v1.json',ROOT/'tools/check_endpoints.py',*[f for f in out.iterdir() if f.is_file()]]
    manifest=[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]
    save(ROOT/'endpoint_manifest.json',{'files':manifest});archive=ROOT/'endpoint_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for r in manifest:tf.add(ROOT/r['file'],arcname=r['file'])
        tf.add(ROOT/'endpoint_manifest.json',arcname='endpoint_manifest.json')
    print(json.dumps({'files':len(manifest)+1,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)
if __name__=='__main__':main()
