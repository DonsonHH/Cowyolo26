"""All histogram statistics plus independent double-precision convex clipping."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import json,math,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'delivery/results/audit'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def polyarea(p):
    if len(p)<3:return 0.
    a=p[0]
    return abs(sum((p[i][0]-a[0])*(p[i+1][1]-a[1])-(p[i][1]-a[1])*(p[i+1][0]-a[0]) for i in range(1,len(p)-1)))/2
def clip(subject,clipper):
    signed=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(clipper,clipper[1:]+clipper[:1]))
    orientation=1 if signed>=0 else -1
    out=[list(map(float,p)) for p in subject]
    for a,b in zip(clipper,clipper[1:]+clipper[:1]):
        def cross(p):return orientation*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
        src=out;out=[]
        if not src:break
        for u,v in zip(src,src[1:]+src[:1]):
            cu,cv=cross(u),cross(v)
            if cu>=-1e-9:out.append(u)
            if (cu>=-1e-9)!=(cv>=-1e-9):
                f=cu/(cu-cv);out.append([u[k]+f*(v[k]-u[k]) for k in [0,1]])
    return out
def quantile_from_counts(h,q):
    target=(int(sum(h))-1)*q/100
    low,high=math.floor(target),math.ceil(target)
    def order(index):
        total=0
        for value,count in enumerate(h):
            total+=int(count)
            if total>index:return value
        raise AssertionError(index)
    return order(low)*(1-(target-low))+order(high)*(target-low)

p=load(ROOT/'protocol/audit_v1.json');s=load(OUT/'summary.json');rows=load(OUT/'objects.json')
assert s['protocol_sha256']==sha(ROOT/'protocol/audit_v1.json') and len(rows)==8888 and s['training_images']==6809
for record in load(ROOT/'delivery/results/artifact_manifest.json'):
    f=ROOT/'delivery'/record['file'];assert f.stat().st_size==record['bytes'] and sha(f)==record['sha256']
train=load(ROOT/'input/train_only.json');images={r['file_name']:r for r in train}
assert len(images)==6809 and all(r['actual_split']=='train' for r in train)
refs={a['annotation_key']:(i,a) for i in train for a in i['reference_annotations']}
assert len(refs)==8888
max_geom=0.;geometry_checks=0
for row in rows:
    image,ref=refs[row['annotation_key']]
    assert row['file_name']==image['file_name'] and row['source_sha256']==image['sha256'] and row['capture_date']==image['capture_date']
    x,y,w,h,t=ref['bbox_xywh_angle_rad'];cx=x+w/2;cy=y+h/2
    corners=[[cx+dx*math.cos(t)-dy*math.sin(t),cy+dx*math.sin(t)+dy*math.cos(t)] for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]
    visible=clip(corners,[[0.,0.],[1280.,0.],[1280.,720.],[0.,720.]])
    value=polyarea(visible);delta=abs(value-row['visible_area']);assert delta<1e-7;max_geom=max(max_geom,delta)
    assert abs(row['visible_reference_fraction']-value/(w*h))<1e-10
    assert row['native_short_side']==min(w,h)
    for size in [192,256,320]:assert abs(row['short_side_at'+str(size)]-min(w,h)*size/1280)<1e-10
    assert abs(row['visible_area_at192']-value*(192/1280)**2)<1e-8;geometry_checks+=1
with np.load(OUT/'all_Y_histograms.npz') as archive:
    bh,rh=archive['body'],archive['background'];assert bh.shape==rh.shape==(8888,256) and bh.dtype==rh.dtype==np.int32
    assert (bh>=0).all() and (rh>=0).all()
    for i,row in enumerate(rows):
        assert int(bh[i].sum())==row['body_raster_pixels'] and int(rh[i].sum())==row['background_ring_pixels']
        for q,key in [(10,'Y_p10'),(50,'Y_median'),(90,'Y_p90')]:assert abs(quantile_from_counts(bh[i],q)-row[key])<1e-10
        background=quantile_from_counts(rh[i],50) if rh[i].sum()>=64 else None
        assert background==row['background_Y_median']
        assert row['absolute_median_contrast']==(abs(row['Y_median']-background) if background is not None else None)
        assert row['fraction_Y_lt64']==int(bh[i,:64].sum())/int(bh[i].sum())
    control_count=0
    for record in load(OUT/'pixel_controls.json'):
        assert sha(OUT/record['file'])==record['sha256']
        with np.load(OUT/record['file']) as ar:
            yy=ar['Y'];masks=ar['masks'];indices=ar['rows'];union=ar['union']
            assert yy.shape==(720,1280) and masks.shape[1:]==yy.shape and set(np.unique(masks))<={0,1}
            assert np.logical_or.reduce(masks.astype(bool),axis=0).astype(np.uint8).tobytes()==union.tobytes()
            for mask,index in zip(masks,indices):
                histogram=np.bincount(yy[mask.astype(bool)],minlength=256)
                assert np.array_equal(histogram,bh[index])
                padded=np.pad(mask.astype(np.int64),((16,16),(16,16)))
                integral=np.pad(np.cumsum(np.cumsum(padded,axis=0),axis=1),((1,0),(1,0)))
                counts=integral[33:,33:]-integral[:-33,33:]-integral[33:,:-33]+integral[:-33,:-33]
                independent_ring=(counts>0)&(union==0)
                histogram=np.bincount(yy[independent_ring],minlength=256)
                assert np.array_equal(histogram,rh[index]),int(index)
                control_count+=1
pairs=load(OUT/'polygon_pairs.json');max_pair_error=0.;maxfrac=0.;pairmax=defaultdict(lambda:[0.,0.])
for pair in pairs:
    a,b=rows[pair['row_a']],rows[pair['row_b']]
    assert a['file_name']==b['file_name']==pair['file_name']
    inter=polyarea(clip(a['visible_polygon'],b['visible_polygon']))
    error=abs(inter-pair['intersection_area']);assert error<.25;max_pair_error=max(max_pair_error,error)
    fraction=inter/min(a['visible_area'],b['visible_area'])
    delta=abs(fraction-pair['intersection_over_min_area']);assert delta<3e-6;maxfrac=max(maxfrac,delta)
    for index in [pair['row_a'],pair['row_b']]:
        pairmax[index][0]=max(pairmax[index][0],pair['polygon_IoU'])
        pairmax[index][1]=max(pairmax[index][1],pair['intersection_over_min_area'])
for i,row in enumerate(rows):assert [row['max_polygon_IoU'],row['max_overlap_over_min_area']]==pairmax[i]
def summary(rr):
    dark=lambda r:r['Y_median']<=80
    low=lambda r:r['absolute_median_contrast'] is not None and r['absolute_median_contrast']<=15
    return {'objects':len(rr),'dark_proxy_median_le80':sum(map(dark,rr)),'low_contrast_proxy_le15':sum(map(low,rr)),
        'unavailable_background':sum(r['absolute_median_contrast'] is None for r in rr),'short_side192_lt24':sum(r['short_side_at192']<24 for r in rr),
        'overlap_min_fraction_ge01':sum(r['max_overlap_over_min_area']>=.1 for r in rr),'truncated_visible_fraction_lt099':sum(r['visible_reference_fraction']<.99 for r in rr),
        'dark_and_lowcontrast':sum(dark(r) and low(r) for r in rr),
        'Y_median_percentiles':np.percentile([r['Y_median'] for r in rr],[0,10,25,50,75,90,100]).tolist(),
        'absolute_median_contrast_percentiles':np.percentile([r['absolute_median_contrast'] for r in rr if r['absolute_median_contrast'] is not None],[0,10,25,50,75,90,100]).tolist(),
        'short_side192_percentiles':np.percentile([r['short_side_at192'] for r in rr],[0,10,25,50,75,90,100]).tolist()}
assert summary(rows)==s['all_objects']
for date,stored in s['by_date'].items():assert summary([r for r in rows if r['capture_date']==date])==stored
assert s['validation_images_read']==s['holdout_images_read']==s['source_video_frames_read']==s['new_model_forwards']==s['new_training_updates']==0
result={'status':'ALL8888_GEOMETRIES_HISTOGRAMS_THRESHOLDS_PAIRS_AND_DATE_AGGREGATES_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'geometry_checks':geometry_checks,'histograms_checked':17776,'pixel_control_objects':control_count,'polygon_pairs_checked':len(pairs),
    'maximum_visible_area_error':max_geom,'maximum_FP32_pair_area_error':max_pair_error,'maximum_FP32_pair_fraction_error':maxfrac,
    'training_images':6809,'all_objects':s['all_objects'],'source_only_training_asserted':True,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
dest=ROOT/'results/independent_verification.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
