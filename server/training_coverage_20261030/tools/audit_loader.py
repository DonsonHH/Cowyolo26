"""One delivered epoch of the real train-only augmentation loader, zero networks."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,socket,json,hashlib,time
import cv2,numpy as np,torch,ultralytics
from ultralytics.cfg import get_cfg
from ultralytics.data.build import build_yolo_dataset,build_dataloader
from ultralytics.utils.torch_utils import init_seeds
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'input'))
from rotation_only import rotate_training_batch
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')

def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    cv2.setNumThreads(1);torch.set_num_threads(2)
    p=load(ROOT/'protocol/loader_v1.json');e=load(ROOT/'protocol/loader_execution_v1.json')
    assert sha(ROOT/'protocol/loader_v1.json')==e['protocol_sha256']
    for name,digest in e['files_sha256'].items():assert sha(ROOT/name)==digest,name
    assert ultralytics.__version__=='8.4.63' and torch.__version__=='2.8.0+cu128'
    train=load(ROOT/'input/train_only.json');allowed={r['image_alias'] for r in train}
    assert len(allowed)==6809
    init_seeds(26,deterministic=True)
    config=get_cfg(overrides=p['loader_args'])
    dataset=build_yolo_dataset(config,p['train_images_path'],32,{'nc':1,'names':{0:'cow'},'channels':3},mode='train',rect=False,stride=32)
    assert len(dataset)==6809 and sum(len(r['cls']) for r in dataset.labels)==8888
    assert set(dataset.im_files)==allowed
    loader=build_dataloader(dataset,batch=32,workers=2,shuffle=True,rank=-1,drop_last=False)
    assert len(loader)==213
    rng=torch.Generator(device='cpu');rng.manual_seed(710052)
    out=ROOT/'results/loader';out.mkdir(parents=True,exist_ok=False)
    controls=out/'pixel_controls';controls.mkdir()
    rows=[];images=[];batches=[];rotation_counts=Counter();started=time.monotonic_ns()
    for index,batch in enumerate(loader):
        assert batch['img'].dtype==torch.uint8 and batch['img'].shape[1:]==(3,192,192)
        turns=torch.randint(0,4,(len(batch['img']),),generator=rng)
        rotated,boxes=rotate_training_batch(batch['img'],batch['bboxes'],batch['batch_idx'],turns)
        assert torch.equal(boxes[:,2]*boxes[:,3],batch['bboxes'][:,2]*batch['bboxes'][:,3])
        rotation_counts.update(turns.tolist())
        pixels=rotated.numpy();bb=boxes.numpy();bi=batch['batch_idx'].numpy().astype(int)
        assert np.isfinite(bb).all() and (bb[:,2:]>0).all()
        if index<3:
            file=controls/('batch'+str(index)+'.npz')
            np.savez_compressed(file,RGB=pixels,boxes=bb,batch_indices=bi,turns=turns.numpy())
        for j,rgb in enumerate(pixels):
            rgb=np.ascontiguousarray(rgb.transpose(1,2,0));yy=cv2.cvtColor(rgb,cv2.COLOR_RGB2YCrCb)[:,:,0]
            selected=np.flatnonzero(bi==j);xyxy=[]
            for k in selected:
                cx,cy,w,h=bb[k].astype(float)*192
                xyxy.append([cx-w/2,cy-h/2,cx+w/2,cy+h/2])
            union=np.zeros((192,192),np.uint8)
            masks=[]
            for box in xyxy:
                a,b,c,d=box;mask=np.zeros((192,192),np.uint8)
                x0=max(0,int(np.floor(a)));y0=max(0,int(np.floor(b)));x1=min(192,int(np.ceil(c)));y1=min(192,int(np.ceil(d)))
                assert x1>x0 and y1>y0
                mask[y0:y1,x0:x1]=1;union|=mask;masks.append(mask)
            for k,(box,mask) in enumerate(zip(xyxy,masks)):
                a,b,c,d=box;body=yy[mask>0];assert len(body)>0
                ring=(cv2.dilate(mask,np.ones((5,5),np.uint8))>0)&(union==0)
                background=yy[ring];median=float(np.median(body));bg=float(np.median(background)) if len(background)>=4 else None
                maxover=0.
                for l,other in enumerate(xyxy):
                    if l==k:continue
                    x,y,z,w=other;inter=max(0,min(c,z)-max(a,x))*max(0,min(d,w)-max(b,y))
                    maxover=max(maxover,inter/min((c-a)*(d-b),(z-x)*(w-y)))
                rows.append({'row':len(rows),'batch':index,'image_in_batch':j,'anchor_file':batch['im_file'][j],
                    'box_index_in_image':k,'xyxy_192':box,'short_side':min(c-a,d-b),'area':(c-a)*(d-b),
                    'body_raster_pixels':len(body),'Y_median':median,'background_Y_median':bg,'background_pixels':len(background),
                    'absolute_median_contrast':abs(median-bg) if bg is not None else None,'max_overlap_over_min_area':maxover})
            images.append({'batch':index,'image_in_batch':j,'anchor_file':batch['im_file'][j],'label_count':len(selected),'rotation_turns':int(turns[j]),
                'RGB_sha256':hashlib.sha256(np.ascontiguousarray(pixels[j]).tobytes()).hexdigest()})
        batches.append({'batch':index,'images':len(pixels),'label_rows':len(bb),'RGB_batch_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),
            'boxes_sha256':hashlib.sha256(bb.tobytes()).hexdigest(),'batch_indices_sha256':hashlib.sha256(bi.tobytes()).hexdigest()})
        if index%50==0:print(json.dumps({'delivered_batches':index+1,'delivered_images':len(images),'augmented_label_rows':len(rows),'network_forwards':0}),flush=True)
    assert len(batches)==213 and len(images)==6809 and sum(rotation_counts.values())==6809
    # Stop prefetch workers; any prefetched future train samples are not counted.
    if hasattr(loader.iterator,'_shutdown_workers'):loader.iterator._shutdown_workers()
    save(out/'objects.json',rows);save(out/'images.json',images);save(out/'batches.json',batches)
    summary={'status':'ONE_REAL_TRAIN_LOADER_EPOCH213_BATCHES6809_IMAGES_WITHOUT_NETWORK_FORWARD',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/loader_v1.json'),
        'delivered_batches':213,'delivered_images':6809,'augmented_label_rows':len(rows),'rotation_counts':dict(rotation_counts),
        'short_side_lt24':sum(r['short_side']<24 for r in rows),'short_side_lt16':sum(r['short_side']<16 for r in rows),
        'short_side_percentiles':np.percentile([r['short_side'] for r in rows],[0,10,25,50,75,90,100]).tolist(),
        'dark_AABB_proxy_median_le80':sum(r['Y_median']<=80 for r in rows),
        'low_contrast_AABB_proxy_le15':sum(r['absolute_median_contrast'] is not None and r['absolute_median_contrast']<=15 for r in rows),
        'overlap_AABB_min_fraction_ge01':sum(r['max_overlap_over_min_area']>=.1 for r in rows),
        'image_label_count_distribution':dict(Counter(r['label_count'] for r in images)),
        'dataset_transform_repr':str(dataset.transforms),'actual_loader_workers':loader.num_workers,'pin_memory':loader.pin_memory,
        'CPU_loader_not_formal_training_record':True,'worker_prefetch_not_counted_as_delivered':True,
        'validation_or_holdout_or_source_video_pixels':0,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False,
        'wall_s':(time.monotonic_ns()-started)/1e9}
    save(out/'summary.json',summary)
    save(ROOT/'results/loader_manifest.json',[{'file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()])
    print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
