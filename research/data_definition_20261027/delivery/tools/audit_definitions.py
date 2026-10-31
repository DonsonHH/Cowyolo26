"""Data composition and geometric witnesses, not alternative detector accuracy."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,os,shutil
import cv2,numpy as np
from PIL import Image,ImageOps,ImageDraw

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'data_definition'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2))


def geometry(a,b):
    x1=max(a[0],b[0]);y1=max(a[1],b[1]);x2=min(a[2],b[2]);y2=min(a[3],b[3])
    inter=max(0,x2-x1)*max(0,y2-y1)
    ga=max(0,a[2]-a[0])*max(0,a[3]-a[1]);pa=max(0,b[2]-b[0])*max(0,b[3]-b[1])
    return {'iou':inter/max(ga+pa-inter,1e-12),'intersection_over_prediction':inter/max(pa,1e-12),
            'prediction_reference_area_ratio':pa/max(ga,1e-12),'reference_area':ga,'prediction_area':pa}


def clipped(box,w=1920,h=1080):
    return [max(0,box[0]),max(0,box[1]),min(w,box[2]),min(h,box[3])]


def main():
    cv2.setNumThreads(2)
    OUT=ROOT/'results/audit';OUT.mkdir(parents=True,exist_ok=False)
    for d in ['training_samples','toros_views']:(OUT/d).mkdir()
    pp=ROOT/'protocol/definition_audit_v1.json';protocol=json.loads(pp.read_text())
    manifest_path=PROJECT/'data/opencows2020/derived_detection/manifest.json'
    manifest=json.loads(manifest_path.read_text());composition={};annotation=[]
    for split in sorted({r['split'] for r in manifest}):
        selected=[r for r in manifest if r['split']==split]
        composition[split]=dict(Counter('synthetic' if r['synthetic_by_readme'] else 'real' for r in selected))
    assert composition['train']=={'real':2596,'synthetic':3317} or composition['train']=={'synthetic':3317,'real':2596}
    for row in manifest:
        if row['split'] not in ['train','val']:continue
        lines=[line.split() for line in Path(row['derived_label']).read_text().splitlines() if line.strip()]
        annotation.append({'source_image':Path(row['image']).name,'split':row['split'],'synthetic':row['synthetic_by_readme'],
                           'boxes':len(lines),'clipped_boxes':row['clipped_boxes'],'removed_boxes':row['removed_boxes']})
    samples=[]
    for synthetic in [False,True]:
        candidates=[r for r in manifest if r['split']=='train' and r['synthetic_by_readme']==synthetic]
        candidates.sort(key=lambda r:hashlib.sha256(('definition-audit-v1:'+r['image']).encode()).hexdigest())
        for row in candidates[:6]:
            path=Path(row['image']);assert sha(path)==row['sha256']
            image=cv2.imread(str(path));assert image is not None
            h,w=image.shape[:2];labels=[]
            for line in Path(row['derived_label']).read_text().splitlines():
                if not line.strip():continue
                cls,cx,cy,bw,bh=map(float,line.split())
                box=[(cx-bw/2)*w,(cy-bh/2)*h,(cx+bw/2)*w,(cy+bh/2)*h]
                labels.append(box)
                cv2.rectangle(image,(round(box[0]),round(box[1])),(round(box[2]),round(box[3])),(0,220,255),3)
            target=OUT/'training_samples'/f'{"synthetic" if synthetic else "real"}_{path.stem}.jpg'
            assert cv2.imwrite(str(target),image,[cv2.IMWRITE_JPEG_QUALITY,93])
            samples.append({'source':str(path),'source_sha256':row['sha256'],'source_split':'train','synthetic_by_readme':synthetic,
                            'width':w,'height':h,'cleaned_label_path':row['derived_label'],'cleaned_label_sha256':sha(row['derived_label']),
                            'boxes':labels,'review_image':str(target.relative_to(OUT)),'review_image_sha256':sha(target)})
    gt_path=PROJECT/'phase2/data/mendeley_counting/extracted/Ground Truth/gt.txt'
    gt=defaultdict(list)
    for r in csv.reader(gt_path.open()):
        r=list(map(float,r));gt[int(r[0])].append({'reference_id':int(r[1]),'box':clipped([r[2],r[3],r[2]+r[4],r[3]+r[5]])})
    model_specs=[('generic',PROJECT/'phase3_diagnosis/results/capture/generic/raw_detector_boxes.csv'),
                 ('pilot',PROJECT/'phase3_diagnosis/results/capture/pilot/raw_detector_boxes.csv')]
    model_specs += [(f'epoch20_seed{seed}',PROJECT/f'event_diagnosis/results/capture/epoch20_seed{seed}/raw_detector_boxes.csv') for seed in [26,27,28]]
    raw={};descriptions=[];witnesses=[]
    for name,path in model_specs:
        by_frame=defaultdict(list)
        for row in csv.DictReader(path.open()):
            by_frame[int(row['frame'])].append({'box':clipped([float(row[k]) for k in ['x1','y1','x2','y2']]),'confidence':float(row['confidence'])})
        raw[name]=by_frame;values=[];flagged=[];nonempty=0
        for frame in range(479):
            for g in gt[frame]:
                if geometry(g['box'],g['box'])['reference_area']<=0:continue
                nonempty+=1
                candidates=[{**geometry(g['box'],p['box']),'box':p['box'],'confidence':p['confidence']} for p in by_frame[frame]]
                if not candidates:continue
                best=max(candidates,key=lambda r:r['iou'])
                record={'model':name,'frame':frame,'reference_id':g['reference_id'],'reference_box':g['box'],**best}
                record['review_flag']=(record['intersection_over_prediction']>=.9 and .15<=record['prediction_reference_area_ratio']<=.75 and record['iou']<.5)
                values.append(record)
                if record['review_flag']:flagged.append(record)
        assert nonempty==sum(len(v) for v in gt.values())
        selected=min(flagged,key=lambda r:(r['frame'],r['reference_id'])) if flagged else None
        if selected:witnesses.append(selected)
        describe={'model':name,'raw_csv_sha256':sha(path),'publisher_rows':nonempty,'rows_with_same_frame_any_raw_candidate':len(values),
                  'rows_flagged_for_contained_smaller_box_review':len(flagged),'review_witness':selected,
                  'scope':'HighestIoU candidate per publisher row; no one-to-one assignment, not precision/recall and not extra true positives'}
        descriptions.append(describe)
        save(OUT/f'{name}_row_geometry.json',values)
    source=PROJECT/'phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4'
    capture_frames=sorted(set(protocol['Toros_evidence']['visual_source_frames'])|{r['frame'] for r in witnesses})
    cap=cv2.VideoCapture(str(source));assert (cap.get(5),int(cap.get(7)))==(30.,479)
    views=[]
    for frame in range(max(capture_frames)+1):
        ok,image=cap.read();assert ok
        if frame not in capture_frames:continue
        for name,_ in model_specs:
            view=image.copy()
            for r in gt[frame]:
                b=r['box'];cv2.rectangle(view,(round(b[0]),round(b[1])),(round(b[2]),round(b[3])),(65,230,65),3)
                cv2.putText(view,f'GT {r["reference_id"]}',(max(0,round(b[0])),max(35,round(b[1])-12)),cv2.FONT_HERSHEY_SIMPLEX,.85,(65,230,65),2)
            for r in raw[name][frame]:
                b=r['box'];cv2.rectangle(view,(round(b[0]),round(b[1])),(round(b[2]),round(b[3])),(0,180,255),3)
                cv2.putText(view,f'raw {r["confidence"]:.2f}',(max(0,round(b[0])),max(60,round(b[1])+24)),cv2.FONT_HERSHEY_SIMPLEX,.75,(0,180,255),2)
            cv2.rectangle(view,(0,0),(1920,45),(18,24,28),-1)
            cv2.putText(view,f'{name} | Toros frame {frame} | green: publisher box; orange: frozen RAW output',(18,32),cv2.FONT_HERSHEY_SIMPLEX,.8,(240,242,240),2)
            target=OUT/'toros_views'/f'{name}_f{frame}.jpg';assert cv2.imwrite(str(target),view,[cv2.IMWRITE_JPEG_QUALITY,93])
            views.append({'model':name,'frame':frame,'source_frame':frame,'file':str(target.relative_to(OUT)),'sha256':sha(target),'size':[1920,1080]})
    cap.release()
    contact=Image.new('RGB',(3*560,4*350),(20,26,30));draw=ImageDraw.Draw(contact)
    for i,r in enumerate(samples):
        x=i%3*560;y=i//3*350
        with Image.open(OUT/r['review_image']) as im:tile=ImageOps.contain(im.convert('RGB'),(550,310));contact.paste(tile,(x,y+30))
        draw.text((x+6,y+7),f'{"synthetic" if r["synthetic_by_readme"] else "real"} {Path(r["source"]).name} TRAIN',fill='white')
    contact.save(OUT/'public_training_samples.jpg',quality=94)
    result={'status':'DATA_COMPOSITION_AND_BOX_DEFINITION_REVIEW_MATERIALS_READY','job_id':os.environ['SLURM_JOB_ID'],
            'protocol_sha256':sha(pp),'opencows_manifest_sha256':sha(manifest_path),'composition':composition,
            'train_synthetic_fraction':3317/5913,'annotation_counts_train_val':annotation,'train_visual_samples':samples,
            'toros_source_sha256':sha(source),'toros_gt_sha256':sha(gt_path),'toros_raw_geometry_descriptions':descriptions,
            'toros_visual_views':views,'captured_toros_frames':capture_frames,
            'new_model_forward_or_training':False,'frozen_metrics_changed':False,
            'synth_mother_image_linkage_resolved':False,'view_or_breed_causal_explanation_proven':False}
    save(OUT/'summary.json',result)
    print(json.dumps({'status':result['status'],'composition':composition,'witnesses':witnesses}),flush=True)


if __name__=='__main__':main()
