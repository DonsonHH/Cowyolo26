"""Independent transform and augmenting-path matching of all saved predictions."""
from pathlib import Path
from collections import Counter,defaultdict
import gzip,hashlib,json,math
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def overlap(a,b):
    left=max(a[0],b[0]);right=min(a[2],b[2]);top=max(a[1],b[1]);bottom=min(a[3],b[3])
    inter=max(0,right-left)*max(0,bottom-top)
    union=(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter
    return inter/union if union>0 else 0.


def maximum_matching(gt,pred,threshold):
    adjacency=[[j for j,b in enumerate(pred) if overlap(a,b)>=threshold] for a in gt]
    assigned={}
    def extend(i,seen):
        for j in adjacency[i]:
            if j in seen:continue
            seen.add(j)
            if j not in assigned or extend(assigned[j],seen):assigned[j]=i;return True
        return False
    return sum(extend(i,set()) for i in range(len(gt)))


def expected_boxes(row,orientation):
    boxes=[]
    for cls,cx,cy,w,h in row['expected_float32_rows']:
        assert cls==0
        xs=[(cx-w/2)*1280,(cx+w/2)*1280];ys=[(cy-h/2)*720,(cy+h/2)*720]
        points=[(x,y) for x in xs for y in ys]
        if orientation=='clockwise90':points=[(720-y,x) for x,y in points]
        px,py=zip(*points);boxes.append([min(px),min(py),max(px),max(py)])
    return boxes


def main():
    delivery=ROOT/'delivery';manifest=json.loads((delivery/'delivery_manifest.json').read_text(encoding='utf-8'))
    assert len({r['path'] for r in manifest})==len(manifest)
    for row in manifest:
        p=delivery/row['path'];assert p.resolve().is_relative_to(delivery.resolve())
        assert p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    ppath=delivery/'protocol/orientation_v1.json';protocol=json.loads(ppath.read_text(encoding='utf-8'))
    assert sha(ppath)==sha(ROOT/'protocol/orientation_v1.json')
    selected=json.loads((delivery/'input/selected_validation.json').read_text(encoding='utf-8'))
    by_name={r['file_name']:r for r in selected};assert len(by_name)==1571
    assert sum(len(r['expected_float32_rows']) for r in selected)==1864
    conditions=delivery/'results/control'
    summary=json.loads((conditions/'summary.json').read_text(encoding='utf-8'))
    assert summary['protocol_sha256']==sha(ppath) and summary['new_training_updates']==0
    assert summary['source_Toros_or_candidate_final_images_opened'] is False
    assert sha(delivery/'input/source_checkpoint_freeze.json')==protocol['source_checkpoint_freeze_sha256']
    input_controls=json.loads((conditions/'input_pixel_controls.json').read_text(encoding='utf-8'))
    assert sha(conditions/'input_pixel_controls.json')==summary['input_pixel_controls_sha256']
    assert len(input_controls)==1571
    assert all(r['exact_inverse_pixel_permutation_verified'] for r in input_controls)
    recalculated={};checks=[];max_gt_difference=0.;sample_images=0
    for item in summary['conditions']:
        seed,orientation=item['seed'],item['orientation']
        checkpoint=next(r for r in protocol['checkpoints'] if r['seed']==seed)
        assert item['checkpoint_sha256']==checkpoint['sha256']
        prediction_path=conditions/item['predictions_file'];metric_path=conditions/item['metrics_file']
        assert sha(prediction_path)==item['predictions_sha256'] and sha(metric_path)==item['metrics_sha256']
        with gzip.open(prediction_path,'rt',encoding='utf-8') as file:rows=json.load(file)
        assert [r['file_name'] for r in rows]==[r['file_name'] for r in selected]
        assert len(rows)==1571
        for row in rows:
            original=by_name[row['file_name']];assert row['source_SHA256']==original['sha256']
            assert row['capture_date']==original['capture_date'] and row['orientation']==orientation
            assert row['GT_annotation_IDs']==original['published_annotation_IDs']
            expected=expected_boxes(original,orientation)
            assert len(expected)==len(row['GT_xyxy'])
            difference=max(abs(a-b) for first,second in zip(expected,row['GT_xyxy']) for a,b in zip(first,second))
            max_gt_difference=max(max_gt_difference,difference);assert difference<1e-9
            assert row['image_dimensions_WH']==([1280,720] if orientation=='original' else [720,1280])
            assert all(len(r['xyxy'])==4 and all(math.isfinite(v) for v in r['xyxy']) and math.isfinite(r['confidence']) for r in row['predictions'])
        metrics=json.loads(metric_path.read_text(encoding='utf-8'))
        assert len(metrics)==4
        for metric in metrics:
            confidence,threshold=metric['confidence_threshold'],metric['IoU_threshold']
            totals=Counter();dates=defaultdict(Counter);match_records=metric['image_matches']
            assert len(match_records)==1571
            for row,saved in zip(rows,match_records):
                assert row['file_name']==saved['file_name']
                gt=expected_boxes(by_name[row['file_name']],orientation)
                predictions=[r['xyxy'] for r in row['predictions'] if r['confidence']>=confidence]
                tp=maximum_matching(gt,predictions,threshold)
                actual={'GT':len(gt),'predictions':len(predictions),'TP':tp,'FP':len(predictions)-tp,'FN':len(gt)-tp}
                assert all(saved[k]==v for k,v in actual.items())
                # Published pair indices and IoUs must also describe a valid
                # one-to-one match with this independently calculated size.
                assert len(saved['matches'])==tp
                assert len({r['gt_index'] for r in saved['matches']})==tp
                assert len({r['prediction_index'] for r in saved['matches']})==tp
                for pair in saved['matches']:
                    value=overlap(gt[pair['gt_index']],predictions[pair['prediction_index']])
                    assert value>=threshold and abs(value-pair['IoU'])<1e-9
                totals.update(actual);dates[row['capture_date']].update(actual)
            assert all(metric[k]==v for k,v in totals.items())
            assert {k:dict(v) for k,v in dates.items()}==metric['by_date']
            assert metric['recall']==totals['TP']/totals['GT']
            precision=totals['TP']/totals['predictions'] if totals['predictions'] else None
            assert metric['precision']==precision
            short={'seed':seed,'orientation':orientation,'confidence':confidence,'IoU':threshold,**dict(totals),
                   'recall':metric['recall'],'precision':precision}
            checks.append(short)
            if confidence==.2 and threshold==.5:recalculated[(seed,orientation)]=metric
        for name in protocol['sample_visuals']['files']:
            p=conditions/'sample_overlays'/f"seed{seed}_{orientation}_{Path(name).stem}.jpg"
            with Image.open(p) as image:
                image.load();assert image.size==((1280,720) if orientation=='original' else (720,1280))
            sample_images+=1
    assert len(checks)==24 and sample_images==48
    rng=np.random.default_rng(26);dates=sorted(protocol['source_dates']);paired=[]
    for saved in summary['primary_paired_comparisons']:
        seed=saved['seed'];original=recalculated[(seed,'original')];turned=recalculated[(seed,'clockwise90')]
        denominator=np.asarray([original['by_date'][d]['GT'] for d in dates])
        difference=np.asarray([turned['by_date'][d]['TP']-original['by_date'][d]['TP'] for d in dates])
        sample=rng.integers(0,len(dates),size=(10000,len(dates)))
        values=difference[sample].sum(1)/denominator[sample].sum(1)
        interval=np.quantile(values,[.025,.975]).tolist()
        assert np.array_equal(interval,saved['date_cluster_bootstrap95_percentile'])
        assert saved['original_recall']==original['recall'] and saved['clockwise90_recall']==turned['recall']
        paired.append(saved)
    result={'status':'ALL_ROTATION_GT_TRANSFORMS_AND_24_METRIC_CONDITIONS_INDEPENDENTLY_VERIFIED',
            'manifest_files':len(manifest),'protocol_sha256':sha(ppath),'input_images':1571,
            'labelled_objects_per_condition':1864,'fixed_models':3,'image_orientations':2,
            'prediction_image_records_checked':1571*6,'GT_objects_transformed_checked':1864*6,
            'maximum_independent_GT_transform_difference':max_gt_difference,'metric_conditions':checks,
            'paired_date_cluster_comparisons':paired,'complete_overlay_decodes':sample_images,
            'source_Toros_or_candidate_final_evaluated':False,'new_training_updates':0,
            'source_video_count_failure_cause_proven':False,'whole_goal_complete':False}
    target=ROOT/'results/independent_verification.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['metric_conditions']}),flush=True)


if __name__=='__main__':main()
