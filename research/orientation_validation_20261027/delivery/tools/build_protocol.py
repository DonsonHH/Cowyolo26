"""Fix a paired rotation-only development diagnostic before new predictions."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import hashlib,json,shutil,tarfile

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT.parent/'cows2021_adaptation_20261027'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    frozen=STUDY/'delivery/results/training/all_checkpoints_frozen_before_video.json'
    loaded=STUDY/'delivery/results/labels_v1/prepared_image_label_manifest.json'
    all_rows=json.loads(loaded.read_text(encoding='utf-8'))
    selected=sorted([r for r in all_rows if r['actual_split']=='val'],key=lambda r:r['file_name'])
    assert len(selected)==1571 and sum(len(r['expected_float32_rows']) for r in selected)==1864
    assert all(r['candidate_date_role']=='validation_development_candidate' for r in selected)
    assert len({r['file_name'] for r in selected})==1571
    samples=sorted(selected,key=lambda r:hashlib.sha256(('orientation-control-v1:'+r['file_name']).encode()).hexdigest())[:8]
    freeze=json.loads(frozen.read_text(encoding='utf-8'))
    assert [r['seed'] for r in freeze['conditions']]==[26,27,28]
    p={'name':'Frozen Cows detector paired0/90degree validation control v1',
       'created_UTC':datetime.now(timezone.utc).isoformat(),
       'scope':'Paired development sensitivity test on the same previously used validation images. Not a new independent test or proof of video failure cause.',
       'source_checkpoint_freeze_sha256':sha(frozen),'source_prepared_manifest_sha256':sha(loaded),
       'validation_images':1571,'validation_objects':1864,
       'source_dates':dict(Counter(r['capture_date'] for r in selected)),
       'seeds':[26,27,28],'checkpoints':[{'seed':r['seed'],'path':r['checkpoint'],'sha256':r['checkpoint_sha256']} for r in freeze['conditions']],
       'orientations':['original','clockwise90'],
       'pixel_transformation':'np.rot90(native_cv2_BGR,k=-1).copy(); no interpolation/re-encoding/crop; original source bytes retained',
       'box_transformation':'continuous image edges: [x1,y1,x2,y2] -> [H-y2,x1,H-y1,x2] with output dimensions(H,W)',
       'prediction':{'imgsz':320,'rect':False,'batch':16,'confidence_floor':0.01,'nominal_iou_argument':0.5,'maximum_detections':300,'half':False,'augment':False,'device':0},
       'metrics':{'primary_confidence':0.2,'secondary_confidence':0.01,'box_IoU_thresholds':[0.5,0.75],
                  'matching':'one-to-one maximum-cardinality then maximum-IoU assignment, independent of prediction score after confidence filtering',
                  'primary':'matched cow body recall and precision at confidence0.2/IoU0.5; all6conditions reported',
                  'paired_uncertainty':'resample complete source dates10000times with RNG26; only6date clusters, exploratory bounds',
                  'not_reported':'No native_video passage accuracy, independent-farm claim or PYNQ performance'},
       'sample_visuals':{'selection':'first8 validation basenames ranked by SHA256(orientation-control-v1:+basename), fixed before predictions',
                         'files':[r['file_name'] for r in samples]},
       'new_training_updates':0,'source_Toros_or_candidate_final_images_allowed':False,
       'whole_goal_complete':False}
    protocol=ROOT/'protocol/orientation_v1.json';assert not protocol.exists()
    protocol.parent.mkdir(parents=True,exist_ok=True);protocol.write_text(json.dumps(p,indent=2),encoding='utf-8')
    inputs=ROOT/'input';inputs.mkdir(exist_ok=True)
    (inputs/'selected_validation.json').write_text(json.dumps(selected,indent=2),encoding='utf-8')
    shutil.copyfile(frozen,inputs/'source_checkpoint_freeze.json')
    shutil.copyfile(loaded,inputs/'source_prepared_manifest.json')
    files=sorted(f for folder in ['protocol','input','tools'] for f in (ROOT/folder).rglob('*') if f.is_file() and '__pycache__' not in f.parts)
    records=[{'path':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files]
    index=inputs/'staging_manifest.json';assert not index.exists();index.write_text(json.dumps(records,indent=2),encoding='utf-8')
    bundle=ROOT/'staging.tar.gz';assert not bundle.exists()
    with tarfile.open(bundle,'w:gz') as tar:
        for path in files+[index]:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
    out=ROOT/'results';out.mkdir(exist_ok=True)
    record={'bytes':bundle.stat().st_size,'sha256':sha(bundle),'files':len(records),
            'protocol_sha256':sha(protocol),'validation_images':len(selected),'validation_objects':1864,
            'selected_dates':p['source_dates'],'sample_files':p['sample_visuals']['files'],
            'new_model_predictions_run':False}
    (out/'staging_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record),flush=True)


if __name__=='__main__':main()
