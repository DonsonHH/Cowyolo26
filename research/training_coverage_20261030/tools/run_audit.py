"""All training-only coverage proxies; no detector or identity networks."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import os,sys,socket,json,hashlib,time,itertools
import cv2,numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'input'))
from geometry import reference,area
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def quantile(hist,q):
    total=int(hist.sum());assert total>0
    rank=(total-1)*q/100;lo=int(np.floor(rank));hi=int(np.ceil(rank));cdf=np.cumsum(hist)
    a=int(np.searchsorted(cdf,lo+1));b=int(np.searchsorted(cdf,hi+1))
    return a+(b-a)*(rank-lo)
def summarize(rows):
    median=[r['Y_median'] for r in rows];contrast=[r['absolute_median_contrast'] for r in rows if r['absolute_median_contrast'] is not None]
    return {'objects':len(rows),'dark_proxy_median_le80':sum(r['Y_median']<=80 for r in rows),
        'low_contrast_proxy_le15':sum(r['absolute_median_contrast'] is not None and r['absolute_median_contrast']<=15 for r in rows),
        'unavailable_background':sum(r['absolute_median_contrast'] is None for r in rows),
        'short_side192_lt24':sum(r['short_side_at192']<24 for r in rows),
        'overlap_min_fraction_ge01':sum(r['max_overlap_over_min_area']>=.1 for r in rows),
        'truncated_visible_fraction_lt099':sum(r['visible_reference_fraction']<.99 for r in rows),
        'dark_and_lowcontrast':sum(r['Y_median']<=80 and r['absolute_median_contrast'] is not None and r['absolute_median_contrast']<=15 for r in rows),
        'Y_median_percentiles':np.percentile(median,[0,10,25,50,75,90,100]).tolist(),
        'absolute_median_contrast_percentiles':np.percentile(contrast,[0,10,25,50,75,90,100]).tolist(),
        'short_side192_percentiles':np.percentile([r['short_side_at192'] for r in rows],[0,10,25,50,75,90,100]).tolist()}

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    cv2.setNumThreads(1)
    p=load(ROOT/'protocol/audit_v1.json');e=load(ROOT/'protocol/execution_v1.json')
    assert sha(ROOT/'protocol/audit_v1.json')==e['protocol_sha256']
    for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==digest,name
    train=load(ROOT/'input/train_only.json');assert len(train)==6809
    assert sum(len(r['reference_annotations']) for r in train)==8888
    assert all(r['actual_split']=='train' for r in train)
    out=ROOT/'results/audit';out.mkdir(parents=True,exist_ok=False)
    controls=out/'pixel_controls';controls.mkdir()
    started=time.monotonic_ns();objects=[];image_rows=[];pairs=[];body_hists=[];ring_hists=[];control_rows=[]
    for image_index,item in enumerate(train):
        assert sha(item['image_alias'])==item['sha256'] and Path(item['image_alias']).stat().st_size==item['bytes']
        image=cv2.imread(item['image_alias']);assert image.shape==(720,1280,3)
        yy=cv2.cvtColor(image,cv2.COLOR_BGR2YCrCb)[:,:,0]
        references=[reference(a) for a in item['reference_annotations']]
        masks=[];union=np.zeros(yy.shape,np.uint8)
        for ref in references:
            poly=np.asarray(ref['visible_native_polygon']);mask=np.zeros(yy.shape,np.uint8)
            cv2.fillConvexPoly(mask,np.rint(poly).astype(np.int32),1)
            masks.append(mask);union|=mask
        indices=[];rowstart=len(objects)
        for j,(ref,mask) in enumerate(zip(references,masks)):
            en=ref['visible_reference_AABB'];x0=max(0,int(np.floor(en[0]))-16);y0=max(0,int(np.floor(en[1]))-16)
            x1=min(1280,int(np.ceil(en[2]))+17);y1=min(720,int(np.ceil(en[3]))+17)
            selected=mask[y0:y1,x0:x1]>0;local_y=yy[y0:y1,x0:x1]
            expanded=cv2.dilate(selected.astype(np.uint8),np.ones((33,33),np.uint8))>0
            ring=expanded & ~(union[y0:y1,x0:x1]>0)
            bh=np.bincount(local_y[selected],minlength=256).astype(np.int32)
            rh=np.bincount(local_y[ring],minlength=256).astype(np.int32)
            body_hists.append(bh);ring_hists.append(rh)
            median=quantile(bh,50);background=quantile(rh,50) if int(rh.sum())>=64 else None
            row={'row':len(objects),'file_name':item['file_name'],'capture_date':item['capture_date'],'source_sha256':item['sha256'],
                'annotation_key':ref['annotation_key'],'bbox_xywh_angle_rad':ref['bbox_xywh_angle_rad'],
                'visible_polygon':ref['visible_native_polygon'],'visible_area':ref['visible_reference_area'],
                'visible_reference_fraction':ref['visible_reference_fraction'],'native_short_side':ref['short_side'],
                'short_side_at192':ref['short_side']*.15,'short_side_at256':ref['short_side']*.2,'short_side_at320':ref['short_side']*.25,
                'visible_area_at192':ref['visible_reference_area']*.15**2,'body_raster_pixels':int(bh.sum()),'background_ring_pixels':int(rh.sum()),
                'Y_median':median,'Y_p10':quantile(bh,10),'Y_p90':quantile(bh,90),'fraction_Y_lt64':int(bh[:64].sum())/int(bh.sum()),
                'background_Y_median':background,'absolute_median_contrast':abs(median-background) if background is not None else None,
                'max_polygon_IoU':0.,'max_overlap_over_min_area':0.}
            indices.append(len(objects));objects.append(row)
        for a,b in itertools.combinations(range(len(references)),2):
            pa=np.asarray(references[a]['visible_native_polygon'],np.float32)
            pb=np.asarray(references[b]['visible_native_polygon'],np.float32)
            intersection,_=cv2.intersectConvexConvex(pa,pb,handleNested=True)
            intersection=max(0.,float(intersection));aa=references[a]['visible_reference_area'];bb=references[b]['visible_reference_area']
            unionarea=aa+bb-intersection
            iou=intersection/unionarea if unionarea>0 else 0.
            over=intersection/min(aa,bb)
            assert -.00001<=over<=1.00001
            pairs.append({'file_name':item['file_name'],'row_a':rowstart+a,'row_b':rowstart+b,'intersection_area':intersection,
                'polygon_IoU':iou,'intersection_over_min_area':over})
            for index in [rowstart+a,rowstart+b]:
                objects[index]['max_polygon_IoU']=max(objects[index]['max_polygon_IoU'],iou)
                objects[index]['max_overlap_over_min_area']=max(objects[index]['max_overlap_over_min_area'],over)
        if image_index<32:
            name='train'+str(image_index).zfill(3)+'.npz'
            np.savez_compressed(controls/name,Y=yy,masks=np.stack(masks),rows=np.asarray(indices,dtype=np.int32),union=union)
            control_rows.append({'file_name':item['file_name'],'file':'pixel_controls/'+name,'sha256':sha(controls/name),'object_rows':indices})
        image_rows.append({'file_name':item['file_name'],'capture_date':item['capture_date'],'source_sha256':item['sha256'],
            'label_rows':len(references),'first_object_row':rowstart,'body_pixel_union':int(union.sum())})
        if image_index%1000==0:print(json.dumps({'training_images_read':image_index+1,'objects_audited':len(objects),'model_forwards':0}),flush=True)
    assert len(objects)==8888 and len(image_rows)==6809
    np.savez_compressed(out/'all_Y_histograms.npz',body=np.stack(body_hists),background=np.stack(ring_hists))
    save(out/'objects.json',objects);save(out/'images.json',image_rows);save(out/'polygon_pairs.json',pairs);save(out/'pixel_controls.json',control_rows)
    bydate=defaultdict(list)
    for row in objects:bydate[row['capture_date']].append(row)
    summary={'status':'ALL6809_TRAIN_IMAGES8888_BODY_PROXIES_AUDITED_WITHOUT_NETWORKS','created_UTC':datetime.now(timezone.utc).isoformat(),
        'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/audit_v1.json'),'training_images':6809,'objects':8888,
        'polygon_pairs':len(pairs),'pixel_control_images':32,'pixel_control_objects':sum(len(r['object_rows']) for r in control_rows),
        'all_training_sources_hash_verified':6809,'all_objects':summarize(objects),'by_date':{k:summarize(v) for k,v in sorted(bydate.items())},
        'annotation_field_union':sorted({k for r in train for a in r['reference_annotations'] for k in a}),
        'no_independent_occlusion_or_coatcolor_GT':True,'validation_images_read':0,'holdout_images_read':0,'source_video_frames_read':0,
        'new_model_forwards':0,'new_training_updates':0,'actual_board_actions':0,'whole_goal_complete':False,
        'wall_s':(time.monotonic_ns()-started)/1e9}
    save(out/'summary.json',summary)
    save(ROOT/'results/artifact_manifest.json',[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
    print(json.dumps({k:v for k,v in summary.items() if k!='by_date'}),flush=True)
if __name__=='__main__':main()
