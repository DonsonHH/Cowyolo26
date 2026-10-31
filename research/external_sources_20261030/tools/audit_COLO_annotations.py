from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sig(d,image_id):return sorted((int(a['category_id']),int(a.get('iscrowd',0)),*[float(v) for v in a['bbox']]) for a in d['annotations'] if a['image_id']==image_id)
source=load(ROOT/'results/COLO_zip_metadata_recovered_v2.json');records={r['archive_member']:r for r in source['json_files']};groups={};problems=[]
for name,r in records.items():
 d=load(r['file']);images=d['images'];anns=d['annotations'];byid={i['id']:i for i in images};assert len(byid)==len(images)
 category={c['id']:c['name'] for c in d['categories']};assert category=={0:'cow'}
 ann_ids=set();bad=[]
 for a in anns:
  assert a['id'] not in ann_ids;ann_ids.add(a['id']);assert a['image_id'] in byid and a['category_id']==0
  i=byid[a['image_id']];x,y,w,h=a['bbox'];assert all(math.isfinite(float(z)) for z in [x,y,w,h])
  if min(w,h)<=0 or min(x,y)<-.01 or x+w>i['width']+.01 or y+h>i['height']+.01:bad.append({'annotation_id':a['id'],'bbox':a['bbox'],'WH':[i['width'],i['height']]})
  assert a.get('iscrowd',0)==0
 mapping={Path(i['file_name']).name:{'image':i,'annotation_signature':sig(d,i['id'])} for i in images};assert len(mapping)==len(images)
 groups[name]={'images':len(images),'boxes':len(anns),'invalid_or_out_of_bounds_boxes':bad,'image_records':mapping,'json_sha256':r['sha256']}
 if bad:problems.append({'member':name,'boxes':bad})
base='COLO_COCO/1_top/';light_names=['daylight','indoorlight','infrared'];canonical={};light_counts={}
for lighting in light_names:
 g=groups[base+lighting+'/data.json'];light_counts[lighting]={'images':g['images'],'boxes':g['boxes']}
 for name,record in g['image_records'].items():assert name not in canonical;canonical[name]={**record,'lighting':lighting}
train=groups[base+'train/data.json']['image_records'];test=groups[base+'test/data.json']['image_records']
assert len(canonical)==504 and len(train)==454 and len(test)==50 and not (set(train)&set(test)) and set(train)|set(test)==set(canonical)
for name,row in {**train,**test}.items():assert row['annotation_signature']==canonical[name]['annotation_signature'] and (row['image']['width'],row['image']['height'])==(canonical[name]['image']['width'],canonical[name]['image']['height'])
assert len(groups['COLO_COCO/a1_t2s/train/data.json']['image_records'])==504
for name,row in groups['COLO_COCO/a1_t2s/train/data.json']['image_records'].items():assert name in canonical and row['annotation_signature']==canonical[name]['annotation_signature']
assert set(groups['COLO_COCO/a2_s2t/test/data.json']['image_records'])==set(test)
for name,row in groups['COLO_COCO/a2_s2t/test/data.json']['image_records'].items():assert row['annotation_signature']==test[name]['annotation_signature']
sizes={}
for resolution in [192,256,320,640]:
 short=[]
 for name,r in test.items():
  gain=resolution/max(r['image']['width'],r['image']['height']);short.extend(min(a[4],a[5])*gain for a in r['annotation_signature'])
 sizes[str(resolution)]={'boxes':len(short),'short_edge_lt16px':sum(v<16 for v in short),'short_edge_lt24px':sum(v<24 for v in short),'minimum':min(short),'maximum':max(short)}
test_rows=[]
for name,row in sorted(test.items()):test_rows.append({'file_name':name,'image_id':row['image']['id'],'width':row['image']['width'],'height':row['image']['height'],'lighting':canonical[name]['lighting'],'boxes':row['annotation_signature']})
report={'status':'ALL22_COCO_JSON_STRUCTURES_AND_CANONICAL504_TOP_IMAGES_OVERLAPS_AUDITED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'groups':{n:{k:v for k,v in g.items() if k!='image_records'} for n,g in groups.items()},'canonical_top_light_groups':light_counts,'canonical_top_images':504,'canonical_top_boxes':3950,
 'publisher_top_train_images':454,'publisher_top_test_images':50,'publisher_top_test_boxes':451,'train_test_same_filename_overlap':0,
 'duplicate_configuration_examples_not_new_independent_images':True,'top_test_lighting':dict(Counter(canonical[n]['lighting'] for n in test)),
 'official_test_rows':test_rows,'projected_top_test_box_sizes':sizes,'annotation_problems':problems,
 'contains_track_ID_or_permanent_cow_identity_or_video_times':False,'camera_scope':'Top-View only for intended evaluation; other JSON metadata retained but side-view pixels not requested',
 'all_new_pixels_and_model_predictions_still_unread':True,'new_model_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/COLO_annotation_audit.json';assert not f.exists();f.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k in ['status','canonical_top_images','canonical_top_boxes','publisher_top_train_images','publisher_top_test_images','publisher_top_test_boxes','top_test_lighting','projected_top_test_box_sizes','annotation_problems']}))
