from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict,Counter
import hashlib,json,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    prepared_path=PROJECT/'cows2021_adaptation_20261027/delivery/results/labels_v1/prepared_image_label_manifest.json'
    rows=load(prepared_path);assert len(rows)==8380
    records={};catalogs=[]
    for name in ['train_annotations.json','validation_annotations.json','reserved_test_annotations.json']:
        file=PROJECT/'cows2021_labels_20261027/catalog'/name;j=load(file);images={r['id']:r for r in j['images']};by_image=defaultdict(list)
        for a in j['annotations']:by_image[a['image_id']].append(a)
        for iid,im in images.items():
            name=im['file_name'];assert name not in records
            records[name]={'image':im,'annotations':by_image[iid],'catalog':file.name}
        catalogs.append({'path':str(file.resolve()),'sha256':sha(file)})
    data=[]
    for r in rows:
        ref=records[r['file_name']];assert [a['id'] for a in ref['annotations']]==r['published_annotation_IDs']
        assert ref['image']['width']==r['width']==1280 and ref['image']['height']==r['height']==720
        assert all(a['category_id']==1 and len(a['bbox'])==5 and a['bbox'][2]>0 and a['bbox'][3]>0 for a in ref['annotations'])
        annotations=[{'annotation_key':r['file_name']+':'+str(a['id']),'published_annotation_ID':a['id'],
        'published_catalog':ref['catalog'],'bbox_xywh_angle_rad':a['bbox'],'class':'cow_body_reference'} for a in ref['annotations']]
        data.append({k:r[k] for k in ['file_name','capture_date','source_block','original_filename','published_role','source_XML_sha256',
        'actual_split','width','height','bytes','sha256','image_alias','relative_image_path']}|{'reference_annotations':annotations})
    train=[r for r in data if r['actual_split']=='train'];val=[r for r in data if r['actual_split']=='val']
    assert len(train)==6809 and len(val)==1571 and sum(len(r['reference_annotations']) for r in train)==8888 and sum(len(r['reference_annotations']) for r in val)==1864
    assert not {r['capture_date'] for r in train}&{r['capture_date'] for r in val}
    save(ROOT/'input/images_and_references.json',{'train':train,'val':val})
    models=load(PROJECT/'long_video_fixed_replay_20261029/protocol/replay_v1.json')['models']
    assert len(models)==4 and [m['name'] for m in models]==['official','seed26','seed27','seed28']
    fixed=sorted(val,key=lambda r:hashlib.sha256(('torso-pairs-v1:'+r['file_name']).encode()).hexdigest())[:8]
    protocol={'version':1,'status':'FROZEN_BEFORE_NEW640_PREDICTIONS','created_UTC':datetime.now(timezone.utc).isoformat(),
    'source_dataset':'Cows2021Detection_and_localisation','official_readme_URL':'https://data.bris.ac.uk/datasets/4vnrca7qw1642qlwxjadp87h7/readme.txt',
    'official_paper_URL':'https://arxiv.org/html/2105.01938','source_catalogs':catalogs,
    'prepared_manifest_sha256':sha(prepared_path),'new_pair_manifest_sha256':sha(ROOT/'input/images_and_references.json'),
    'previous_crop_domain_final_sha256':sha(PROJECT/'crop_domain_20261029/results/final_review.json'),
    'models':models,'train_pair_model_name':'seed26','train_images':6809,'train_references':8888,'validation_images':1571,'validation_references':1864,
    'prediction':{'orientation':'clockwise90','imgsz':640,'rect':True,'batch':1,'confidence':.2,'nominal_iou':.5,'max_det':300,'half':False,'augment':False,'device':0},
    'native_box_inverse':'Nativeedgebox=[rot_y1,H-rot_x2,rot_y2,H-rot_x1];H720;fullimage,noROIortracker.',
    'matching':'Reference visible polygon envelope vs nativepredictionAABB:IoU>=.5;maximizecardinalitythenIoU;dummyunmatched.',
    'actual_crop_rounding':'x1/y1=floor, x2/y2=ceil after clamp to nativeimage; no padding; halfopenpixelbox.',
    'metrics':'Referencevisiblepolygoncoverage;referencefractioninactualcrop;polygonIoU;idealGTenvelopeexteriorfraction;notsemanticforegroundsegmentation.',
    'engineering_crop_gate':{'minimum_reference_coverage':.9,'maximum_reference_exterior_fraction':.25},
    'reference_complete_tolerance':1e-8,'all_unmatched_references_and_predictions_retained':True,
    'fixed_validation_sample_names':[r['file_name'] for r in fixed],
    'posthoc_case_rules':['minimum_matched_reference_coverage','maximum_matched_reference_exterior_fraction','maximum_complete_reference_envelope_exterior_fraction','maximum_visible_reference_area_among_unmatched'],
    'reference_crop_visual':'Longaxiswidth,warp4nativecorners to horizontalrectangle;maxlongside800;bilinear,borderRGB127;headtail180ambiguous.',
    'new_training_updates':0,'identity_encoder_forwards':0,'animal_identity_labels_generated':False,
    'current12_counting_pipeline_changed':False,'new_final_test':False,'source_or_Toros_video_pixels_accessed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(ROOT/'protocol/pairs_v1.json',protocol)
    print(json.dumps({'protocol_sha256':sha(ROOT/'protocol/pairs_v1.json'),'train':len(train),'val':len(val),'planned_detector_image_forwards':6809+1571*4,
                      'references':8888+1864,'preset_samples':protocol['fixed_validation_sample_names']}))
if __name__=='__main__':main()
