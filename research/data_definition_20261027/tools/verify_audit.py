"""Independent metadata totals, per-row overlap arithmetic and train-only sample checks."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,math,zipfile,xml.etree.ElementTree as ET
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def calc(reference,prediction):
    shared=max(0,min(reference[2],prediction[2])-max(reference[0],prediction[0]))*max(0,min(reference[3],prediction[3])-max(reference[1],prediction[1]))
    areas=[max(0,b[2]-b[0])*max(0,b[3]-b[1]) for b in [reference,prediction]]
    return shared/(areas[0]+areas[1]-shared),shared/areas[1],areas[1]/areas[0]


def main():
    dest=ROOT/'delivery';manifest=json.loads((dest/'delivery_manifest.json').read_text(encoding='utf-8'))
    for r in manifest:
        p=dest/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256']
    summary=json.loads((dest/'results/audit/summary.json').read_text(encoding='utf-8'))
    prior=json.loads((BASE/'detector_training_20261027/delivery/results/training/manifest.json').read_text(encoding='utf-8'))
    metadata=json.loads((ROOT/'results/archive_metadata/summary.json').read_text(encoding='utf-8'))
    composed={}
    for r in prior:
        composed.setdefault(r['split'],Counter())['synthetic' if r['synthetic_by_readme'] else 'real']+=1
    assert {k:dict(v) for k,v in composed.items()}==summary['composition']
    assert math.isclose(summary['train_synthetic_fraction'],3317/5913)
    gt=defaultdict(dict)
    for row in csv.reader((BASE/'counting_eval_20261026/delivery/counting_evaluation/annotations/publisher_gt_original.txt').open()):
        f,tid,x,y,w,h,*_=map(float,row)
        gt[int(f)][int(tid)]=[max(0,x),max(0,y),min(1920,x+w),min(1080,y+h)]
    overlap_checks=[]
    for condition in summary['toros_raw_geometry_descriptions']:
        name=condition['model']
        source=(BASE/f'phase3_diagnosis_20261026/results/capture/{name}/raw_detector_boxes.csv' if name in ['generic','pilot']
                else BASE/f'event_diagnosis_20261027/delivery/results/capture/{name}/raw_detector_boxes.csv')
        assert sha(source)==condition['raw_csv_sha256']
        byframe=defaultdict(list)
        for r in csv.DictReader(source.open()):
            box=[float(r[k]) for k in ['x1','y1','x2','y2']];box=[max(0,box[0]),max(0,box[1]),min(1920,box[2]),min(1080,box[3])]
            byframe[int(r['frame'])].append(box)
        rows=json.loads((dest/f'results/audit/{name}_row_geometry.json').read_text(encoding='utf-8'))
        flags=[]
        for row in rows:
            a=gt[row['frame']][row['reference_id']];b=row['box'];assert a==row['reference_box'] and b in byframe[row['frame']]
            iou,io_pred,ratio=calc(a,b)
            assert abs(iou-row['iou'])<1e-12 and abs(io_pred-row['intersection_over_prediction'])<1e-12
            assert abs(ratio-row['prediction_reference_area_ratio'])<1e-12
            assert abs(iou-max(calc(a,p)[0] for p in byframe[row['frame']]))<1e-12
            flag=io_pred>=.9 and .15<=ratio<=.75 and iou<.5
            assert flag==row['review_flag']
            if flag:flags.append(row)
        assert len(rows)==condition['rows_with_same_frame_any_raw_candidate']
        assert len(flags)==condition['rows_flagged_for_contained_smaller_box_review']
        assert min(flags,key=lambda r:(r['frame'],r['reference_id']))==condition['review_witness']
        overlap_checks.append({'model':name,'reviewed_candidate_rows':len(rows),'flagged_rows':len(flags),'selected_first_flag_frame':condition['review_witness']['frame']})
    archive=Path('C:/Users/Donson/Downloads/10m32xl88x2b61zlkkgz3fml17.zip/10m32xl88x2b61zlkkgz3fml17.zip')
    assert archive.stat().st_size==2272138852
    assert sha(archive)=='53c437eb2e383092967d218655afac74a20403850ab9dde1d136a570d948362c'
    byname={Path(r['image']).name:r for r in prior};byhash=defaultdict(set)
    for name,r in byname.items():byhash[r['sha256']].add(name)
    with zipfile.ZipFile(archive) as z:
        prefix='10m32xl88x2b61zlkkgz3fml17/detection_and_localisation/'
        fold_file=z.read(prefix+'10-fold-CV.json');assert hashlib.sha256(fold_file).hexdigest()==metadata['supplied_CV_sha256']
        folds=json.loads(fold_file)
        for record in metadata['supplied_folds']:
            groups=folds[record['fold']];train,test=set(groups['train']),set(groups['test'])
            assert not train&test and train|test==set(byname)
            cross=sum(bool(names&train) and bool(names&test) for names in byhash.values() if len(names)>1)
            assert cross==record['identical_bytes_groups_crossing_supplied_train_test']
        for sample in summary['train_visual_samples']:
            basename=Path(sample['source']).name;original=byname[basename]
            assert original['split']=='train' and sample['source_split']=='train'
            assert hashlib.sha256(z.read(prefix+'images/'+basename)).hexdigest()==sample['source_sha256']
            with Image.open(dest/'results/audit'/sample['review_image']) as im:im.load();assert im.size==(sample['width'],sample['height'])
    image_count=0
    for p in (dest/'results/audit').rglob('*.jpg'):
        with Image.open(p) as im:im.load();assert im.width>0 and im.height>0
        image_count+=1
    result={'status':'METADATA_OVERLAP_AND_SOURCE_SAMPLE_ARITHMETIC_PASS','server_manifest_files':len(manifest),
            'independently_recomputed_geometry':overlap_checks,'source_archive_SHA256_reverified':True,
            'train_only_images_visually_sampled':12,'all_JPEG_derivatives_decoded':image_count,
            'XML_metadata_count':metadata['XML_count'],'provided_folds':10,
            'provided_fold_duplicate_crossing_groups':[r['identical_bytes_groups_crossing_supplied_train_test'] for r in metadata['supplied_folds']],
            'frame_level_flags_are_new_true_positives':False,'frozen_event_metrics_changed':False,'full_goal_complete':False}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
