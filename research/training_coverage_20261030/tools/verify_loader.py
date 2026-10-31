"""Delivered augmentations: verify all scalar geometry and96 actual RGB inputs."""
from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import json,hashlib,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'loader_delivery/results/loader'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=load(OUT/'objects.json');images=load(OUT/'images.json');batches=load(OUT/'batches.json')
s=load(ROOT/'results/loader_recovery_local/summary.json')
assert len(rows)==s['augmented_label_rows']==20292 and len(images)==6809 and len(batches)==213
byimage=defaultdict(list)
for r in rows:byimage[r['batch'],r['image_in_batch']].append(r)
assert len({(r['batch'],r['image_in_batch']) for r in images})==6809
allowed={r['image_alias'] for r in load(ROOT/'input/train_only.json')}
for image in images:
    assert image['anchor_file'] in allowed and len(byimage[image['batch'],image['image_in_batch']])==image['label_count']
    current=byimage[image['batch'],image['image_in_batch']]
    for index,r in enumerate(current):
        assert r['box_index_in_image']==index
        a,b,c,d=r['xyxy_192'];assert c>a and d>b
        assert abs(r['short_side']-min(c-a,d-b))<1e-10 and abs(r['area']-(c-a)*(d-b))<1e-8
        overlaps=[]
        for other in current:
            if other['row']==r['row']:continue
            x,y,z,w=other['xyxy_192'];inter=max(0,min(c,z)-max(a,x))*max(0,min(d,w)-max(b,y))
            overlaps.append(inter/min(r['area'],other['area']))
        assert abs(r['max_overlap_over_min_area']-max(overlaps,default=0.))<1e-10
assert s['short_side_lt24']==sum(r['short_side']<24 for r in rows)
assert s['short_side_lt16']==sum(r['short_side']<16 for r in rows)
assert s['dark_AABB_proxy_median_le80']==sum(r['Y_median']<=80 for r in rows)
assert s['low_contrast_AABB_proxy_le15']==sum(r['absolute_median_contrast'] is not None and r['absolute_median_contrast']<=15 for r in rows)
assert s['overlap_AABB_min_fraction_ge01']==sum(r['max_overlap_over_min_area']>=.1 for r in rows)
assert s['short_side_percentiles']==np.percentile([r['short_side'] for r in rows],[0,10,25,50,75,90,100]).tolist()
assert s['rotation_counts']=={str(k):v for k,v in Counter(r['rotation_turns'] for r in images).items()}
actual_pixels=actual_boxes=0;max_luminance_difference=0.;max_inverse=0.
for batch_index in range(3):
    with np.load(OUT/'pixel_controls'/('batch'+str(batch_index)+'.npz')) as ar:
        pixels,bb,bi=ar['RGB'],ar['boxes'],ar['batch_indices']
        assert hashlib.sha256(pixels.tobytes()).hexdigest()==batches[batch_index]['RGB_batch_sha256']
        assert hashlib.sha256(bb.tobytes()).hexdigest()==batches[batch_index]['boxes_sha256']
        assert hashlib.sha256(bi.tobytes()).hexdigest()==batches[batch_index]['batch_indices_sha256']
        for j,rgb in enumerate(pixels):
            image=next(r for r in images if r['batch']==batch_index and r['image_in_batch']==j)
            assert hashlib.sha256(rgb.tobytes()).hexdigest()==image['RGB_sha256']
            assert int(ar['turns'][j])==image['rotation_turns']
            yy=np.array(Image.fromarray(rgb.transpose(1,2,0)).convert('YCbCr'))[:,:,0]
            chosen=bb[bi==j];current=byimage[batch_index,j];assert len(chosen)==len(current)
            union=np.zeros((192,192),bool);masks=[]
            for source,r in zip(chosen,current):
                cx,cy,w,h=[float(v)*192 for v in source]
                expected=[cx-w/2,cy-h/2,cx+w/2,cy+h/2]
                delta=max(abs(a-b) for a,b in zip(expected,r['xyxy_192']));assert delta<1e-10;max_inverse=max(max_inverse,delta)
                a,b,c,d=expected;mask=np.zeros((192,192),bool)
                mask[max(0,math.floor(b)):min(192,math.ceil(d)),max(0,math.floor(a)):min(192,math.ceil(c))]=True
                masks.append(mask);union|=mask
            for mask,r in zip(masks,current):
                value=float(np.median(yy[mask]));difference=abs(value-r['Y_median']);assert difference<=1;max_luminance_difference=max(max_luminance_difference,difference)
                assert int(mask.sum())==r['body_raster_pixels']
                padded=np.pad(mask.astype(np.int64),((2,2),(2,2)))
                integral=np.pad(np.cumsum(np.cumsum(padded,0),1),((1,0),(1,0)))
                expanded=(integral[5:,5:]-integral[:-5,5:]-integral[5:,:-5]+integral[:-5,:-5])>0
                ring=expanded &~union
                assert int(ring.sum())==r['background_pixels']
                if ring.sum()>=4:
                    difference=abs(float(np.median(yy[ring]))-r['background_Y_median']);assert difference<=1;max_luminance_difference=max(max_luminance_difference,difference)
                else:assert r['background_Y_median'] is None
                actual_boxes+=1
            actual_pixels+=1
assert actual_pixels==96
result={'status':'ALL20292_AUGMENTED_GEOMETRIES_AND96_STORED_RGB_IMAGES_INDEPENDENTLY_REVIEWED',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'augmented_label_rows':len(rows),'delivered_images':len(images),'delivered_batches':213,
    'actual_RGB_images_byte_hash_checked':actual_pixels,'actual_stored_label_boxes_and_background_rings_checked':actual_boxes,
    'maximum_box_inverse_error':max_inverse,'maximum_Pillow_vs_OpenCV_Y_median_difference':max_luminance_difference,
    'Y_check_scope':'Pillow_YCbCr_independent_implementation_agrees_with_OpenCV_within1_gray_level_on96_stored_images;not_all6809_pixel_arrays_stored',
    'metadata_anchor_is_not_each_mosaic_component_ID':True,'new_loader_batches':0,'new_model_forwards':0,'whole_goal_complete':False}
dest=ROOT/'results/loader_independent_verification.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
