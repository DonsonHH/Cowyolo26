"""Geometric source search of every frozen gallery crop, no learned encoder."""
from pathlib import Path
import hashlib,json,os,socket,tarfile,time
import cv2,numpy as np
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_source_provenance_20261029')
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n')

def make_template(image,spec,p,sift):
    h,w=image.shape[:2];margin=p['template_feature_mask_fraction_per_side'];mask=np.zeros((h,w),np.uint8)
    mask[round(h*margin):round(h*(1-margin)),round(w*margin):round(w*(1-margin))]=255
    kp,des=sift.detectAndCompute(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),mask)
    return {'image':image,'width':w,'height':h,'keypoints':kp,'points':np.asarray([k.pt for k in kp],np.float32),
            'descriptors':des,'spec':spec}
def image_features(image,p,sift):
    a,b,c,d=p['search_native_crop'];scale=p['search_scale'];cropped=image[b:d,a:c]
    view=cv2.resize(cropped,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
    kp,desc=sift.detectAndCompute(cv2.cvtColor(view,cv2.COLOR_BGR2GRAY),None)
    return np.asarray([k.pt for k in kp],np.float32),desc
def compare(template,image,frame_points,frame_descriptors,p):
    query=template['descriptors'];base={'ratio_matches':0,'inliers':0,'inlier_fraction':0.,'template_inlier_hull_fraction':0.,
                                     'geometry_pass':False,'NCC':None,'mean_absolute_BGR_error':None}
    if query is None or frame_descriptors is None or len(frame_descriptors)<2 or len(query)<8:return base
    matcher=cv2.FlannBasedMatcher({'algorithm':1,'trees':p['FLANN']['trees']},{'checks':p['FLANN']['checks']})
    pairs=matcher.knnMatch(query,frame_descriptors,k=2)
    selected=[a for pair in pairs if len(pair)==2 for a,b in [pair] if a.distance<p['Lowe_ratio']*b.distance]
    # One source keypoint cannot be counted repeatedly as independent support.
    unique={}
    for m in sorted(selected,key=lambda m:m.distance):unique.setdefault(m.trainIdx,m)
    selected=list(unique.values());base['ratio_matches']=len(selected)
    if len(selected)<p['minimum_ratio_matches_to_fit']:return base
    u=np.asarray([template['points'][m.queryIdx] for m in selected],np.float32);v=np.asarray([frame_points[m.trainIdx] for m in selected],np.float32)
    cv2.setRNGSeed(26)
    H,mask=cv2.findHomography(u,v,cv2.RANSAC,p['homography']['max_reprojection_error_search_px'],
                            maxIters=p['homography']['max_iterations'],confidence=p['homography']['confidence'])
    if H is None:return base
    mask=mask.ravel().astype(bool);count=int(mask.sum());base.update(inliers=count,inlier_fraction=count/len(selected))
    if count<4:return base
    hull=cv2.convexHull(u[mask]);hull_fraction=float(cv2.contourArea(hull)/(template['width']*template['height']))
    a,b,c,d=p['search_native_crop'];scale=p['search_scale'];T=np.asarray([[scale,0,-a*scale],[0,scale,-b*scale],[0,0,1.]])
    native=np.linalg.inv(T)@H;native/=native[2,2]
    corners=np.asarray([[0,0],[template['width']-1,0],[template['width']-1,template['height']-1],[0,template['height']-1]],np.float32)
    projected=cv2.perspectiveTransform(corners[None],native)[0]
    predicted=cv2.perspectiveTransform(u[None],H)[0];errors=np.linalg.norm(predicted-v,axis=1)
    visible=float(np.mean((projected[:,0]>=0)&(projected[:,0]<image.shape[1])&(projected[:,1]>=0)&(projected[:,1]<image.shape[0])))
    area=float(abs(cv2.contourArea(projected))/(template['width']*template['height']))
    filters=p['candidate_geometry_filters'];amin,amax=filters['native_mapped_quad_area_ratio_to_template']
    valid=(count>=filters['minimum_inliers'] and count/len(selected)>=filters['minimum_inlier_fraction'] and
           hull_fraction>=filters['minimum_template_inlier_hull_area_fraction'] and visible>=filters['minimum_corner_visible_fraction'] and
           amin<=area<=amax and bool(cv2.isContourConvex(projected)))
    base.update(template_inlier_hull_fraction=hull_fraction,geometry_pass=valid,homography_template_to_native=native.tolist(),
        mapped_native_corners=projected.tolist(),corners_visible_fraction=visible,native_quad_area_ratio_to_template=area,
        reprojection_median_search_px=float(np.median(errors[mask])),
        inlier_template_xy=u[mask].tolist(),inlier_native_xy=((v[mask]/scale)+[a,b]).tolist())
    if not valid:return base
    try:inverse=np.linalg.inv(native)
    except np.linalg.LinAlgError:return base
    warped=cv2.warpPerspective(image,inverse,(template['width'],template['height']),flags=cv2.INTER_LINEAR)
    tw,th=template['width'],template['height'];mask=np.zeros((th,tw),bool);m=p['photometric']['template_interior_fraction_per_side']
    mask[round(th*m):round(th*(1-m)),round(tw*m):round(tw*(1-m))]=True
    original=template['image'];blue=(original[:,:,0]>160)&(original[:,:,1]<130)&(original[:,:,2]<130);mask&=~blue
    ga=cv2.cvtColor(original,cv2.COLOR_BGR2GRAY)[mask].astype(float);gb=cv2.cvtColor(warped,cv2.COLOR_BGR2GRAY)[mask].astype(float)
    if len(ga)>100 and np.std(ga)>1e-6 and np.std(gb)>1e-6:base['NCC']=float(np.corrcoef(ga,gb)[0,1])
    base['mean_absolute_BGR_error']=float(np.mean(abs(original.astype(float)[mask]-warped.astype(float)[mask])))
    base['photometric_valid_pixels']=int(mask.sum());return base

def rank(row):return (row['geometry_pass'],row['NCC'] if row['NCC'] is not None else -2,row['inliers'],-row.get('reprojection_median_search_px',1e10),-row.get('source_frame0',0))
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(4);cv2.setRNGSeed(26)
    p=load(ROOT/'protocol/geometry_v1.json');assert sha(p['source_video'])==p['source_sha256']
    out=ROOT/'results/geometry_coarse';out.mkdir(parents=True,exist_ok=False)
    sift=cv2.SIFT_create(**p['SIFT']);controls=[];control_ok=True
    for source in p['pilot_known_warp_controls']:
        assert sha(source['source_native_photo'])==source['source_native_sha256'];native=cv2.imread(source['source_native_photo']);assert native is not None
        a,b,c,d=source['known_native_crop_box'];template_image=cv2.rotate(native[b:d,a:c],cv2.ROTATE_90_COUNTERCLOCKWISE)
        points,des=image_features(native,p,sift);template=make_template(template_image,source,p,sift);result=compare(template,native,points,des,p)
        corners=np.asarray([[0,0],[template['width']-1,0],[template['width']-1,template['height']-1],[0,template['height']-1]],np.float32)
        known=np.asarray([[0,-1,c-1],[1,0,b],[0,0,1.]],float)
        if 'homography_template_to_native' in result:
            actual=cv2.perspectiveTransform(corners[None],np.asarray(result['homography_template_to_native']))[0]
            expected=cv2.perspectiveTransform(corners[None],known)[0];corner_error=float(np.max(np.linalg.norm(actual-expected,axis=1)))
        else:corner_error=None
        control_ok &= result['geometry_pass'] and result['NCC'] is not None and result['NCC']>.9 and corner_error<5
        rng=np.random.default_rng(26);noise=rng.integers(0,256,template_image.shape,np.uint8)
        negative=compare(make_template(noise,source,p,sift),native,points,des,p)
        control_ok &= not negative['geometry_pass']
        scrambled=template_image.copy();half=scrambled.shape[1]//2;scrambled=np.concatenate([scrambled[:,half:],scrambled[:,:half]],axis=1)
        scramble=compare(make_template(scrambled,source,p,sift),native,points,des,p)
        control_ok &= not (scramble['geometry_pass'] and scramble['NCC'] is not None and scramble['NCC']>.9)
        controls.append({'source':source,'known_warp_positive':result,'maximum_native_corner_error':corner_error,
                         'noise_negative':negative,'scramble_negative':scramble})
    save(out/'controls.json',{'passed':bool(control_ok),'records':controls,'scope':'Known-image-warp geometry sanity only, not cow identity accuracy'})
    assert control_ok,'Known-source controls failed; do not run source search'
    templates=[]
    for r in p['gallery_images']:
        assert sha(r['path'])==r['sha256'];image=cv2.imread(r['path']);assert image is not None and list(image.shape[1::-1])==[r['width'],r['height']]
        templates.append(make_template(image,r,p,sift))
    cap=cv2.VideoCapture(p['source_video']);assert cap.isOpened();top=[[] for _ in templates];feature_counts=[];metrics=[];started=time.perf_counter();frames=0
    try:
        for frame in range(p['decode_end0_exclusive']):
            ok,image=cap.read();assert ok,frame
            if frame%p['coarse_stride']:continue
            points,des=image_features(image,p,sift);feature_counts.append({'frame0':frame,'source_keypoints':len(points)})
            for i,template in enumerate(templates):
                row=compare(template,image,points,des,p);row['source_frame0']=frame
                brief={k:v for k,v in row.items() if k not in ['homography_template_to_native','mapped_native_corners','inlier_template_xy','inlier_native_xy']}
                metrics.append({'template_index':i,**brief});top[i]=sorted(top[i]+[row],key=rank,reverse=True)[:p['retained_per_template']]
            frames+=1
            if frames%100==0:print(json.dumps({'coarse_frames':frames,'source_frame0':frame,'elapsed_s':time.perf_counter()-started}),flush=True)
    finally:cap.release()
    assert frames==p['coarse_expected_frames']==435
    rows=[{'template_index':i,'gallery':t['spec'],'template_keypoints':len(t['points']),'top':top[i]} for i,t in enumerate(templates)]
    save(out/'top_results.json',rows);save(out/'all_metrics.json',metrics);save(out/'frame_features.json',feature_counts)
    summary={'status':'ALL30_FROZEN_GALLERY_CROPS_GEOMETRIC_SEARCH_435_SOURCE_FRAMES_COMPLETE',
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/geometry_v1.json'),
        'coarse_frames':frames,'template_count':len(templates),'template_frame_comparisons':len(metrics),
        'templates_with_geometry_candidate':sum(r['top'][0]['geometry_pass'] for r in rows),
        'best_each':[{'template_index':r['template_index'],'anonymous_ID':r['gallery']['published_anonymous_ID'],
                     'filename':r['gallery']['filename'],'frame0':r['top'][0]['source_frame0'],'NCC':r['top'][0]['NCC'],
                     'inliers':r['top'][0]['inliers'],'geometry_pass':r['top'][0]['geometry_pass']} for r in rows],
        'elapsed_s':time.perf_counter()-started,'source_identity_mapping_certified':False,'new_identity_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
    save(out/'summary.json',summary);print(json.dumps(summary),flush=True)
    files=[ROOT/'protocol/geometry_v1.json',ROOT/'tools/geometry_probe.py',*[f for f in out.rglob('*') if f.is_file()]]
    manifest=[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]
    save(ROOT/'geometry_manifest.json',{'files':manifest});archive=ROOT/'geometry_coarse_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for r in manifest:tf.add(ROOT/r['file'],arcname=r['file'])
        tf.add(ROOT/'geometry_manifest.json',arcname='geometry_manifest.json')
    print(json.dumps({'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'files':len(manifest)+1}),flush=True)
if __name__=='__main__':main()
