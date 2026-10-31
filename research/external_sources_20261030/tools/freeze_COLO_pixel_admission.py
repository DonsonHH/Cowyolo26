from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
audit=load(ROOT/'results/COLO_annotation_audit.json');capture=load(ROOT/'results/COLO_zip_metadata_recovered_v2.json');entries=load(ROOT/'evidence/COLO_zip_metadata_v2/entries.json')
records={r['archive_member']:load(r['file']) for r in capture['json_files']};base='COLO_COCO/1_top/'
train=records[base+'train/data.json'];test=records[base+'test/data.json'];byname={i['file_name']:i for i in train['images']};selected=[]
lighting={i['file_name']:name for name in ['daylight','indoorlight','infrared'] for i in records[base+name+'/data.json']['images']}
for name in ['daylight','indoorlight','infrared']:
 options=sorted(f for f in byname if lighting[f]==name)
 for index in [0,len(options)//2]:selected.append(options[index])
problem_ids={r['annotation_id'] for r in audit['groups'][base+'train/data.json']['invalid_or_out_of_bounds_boxes']}
edge_names=sorted({next(i['file_name'] for i in train['images'] if i['id']==a['image_id']) for a in train['annotations'] if a['id'] in problem_ids})
for name in edge_names:
 if name not in selected:selected.append(name)
 if len(selected)==8:break
assert len(selected)==len(set(selected))==8 and not set(selected)&{i['file_name'] for i in test['images']}
entrymap={e['name']:e for e in entries};rows=[]
for name in selected:
 image=byname[name];member=base+'train/'+name;e=entrymap[member]
 rows.append({'file_name':name,'lighting':lighting[name],'image':image,'annotations':[a for a in train['annotations'] if a['image_id']==image['id']],
  'archive_member':member,'zip_entry':e,'role':'publisher_train_only_pixel_QA_not_model_evaluation_or_training'})
plan={'status':'FROZEN_BEFORE_FIRST_COLO_IMAGE_PIXEL_DECODE','created_UTC':datetime.now(timezone.utc).isoformat(),
 'annotation_audit_sha256':sha(ROOT/'results/COLO_annotation_audit.json'),'release_metadata_sha256':sha(ROOT/'evidence/data_endpoint_probes/COLO_release.response'),
 'purpose':'Check image dimensions, overhead view, unburned raw inputs, and annotation object boundary; no predictions or model selection',
 'selection':'first and median filename within each3 lighting strata among publisher train plus first2 remaining boundary-problem train images',
 'selected_rows':rows,'image_count':8,'publisher_test50_images_not_requested':True,'new_model_forwards':0,
 'rendering_does_not_modify_original_annotations_or_inputs':True,'known_top_test_degenerate_box_ID127_image20154_preserved_unmodified':True,
 'test50_has451_annotations_one_zero_width_and15_small_overshoots_before_any_predictions':True,
 'quantitative_test_or_new_training_not_yet_admitted':True,'whole_goal_complete':False}
f=ROOT/'protocol/COLO_train8_pixel_admission_v1.json';assert not f.exists();f.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8');print(json.dumps({'pixel_QA_train_images':8,'test_pixels_requested':0,'new_forwards':0}))
