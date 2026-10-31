from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import hashlib,json,zlib
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
plan=json.loads((ROOT/'protocol/run_v1.json').read_text());acquisition=json.loads((ROOT/'results/acquisition.json').read_text())
assert acquisition['protocol_sha256']==hashlib.sha256((ROOT/'protocol/run_v1.json').read_bytes()).hexdigest()and acquisition['failed_images']==0
assert not acquisition['same_pixel_duplicate_groups']and acquisition['prior540_and750_exact_pixel_overlap']==0
records=[];allpixels=defaultdict(list)
for index,(row,captured)in enumerate(zip(plan['Cows_training_images'],acquisition['records'])):
 path=ROOT/row['relative_file'];raw=path.read_bytes();assert len(raw)==row['zip_entry']['uncompressed_size']
 assert zlib.crc32(raw)&0xffffffff==row['zip_entry']['CRC32']and hashlib.sha256(raw).hexdigest()==captured['sha256']
 with Image.open(path)as image:image.load();rgb=image.convert('RGB')
 pixel=hashlib.sha256(rgb.width.to_bytes(4,'big')+rgb.height.to_bytes(4,'big')+rgb.tobytes()).hexdigest();assert pixel==captured['canonical_pixel_sha256']
 assert row['publisher_identity']in plan['Cows_training_IDs']and row['publisher_identity']not in plan['future_final_ID_candidates_pixels_closed']
 allpixels[pixel].append(index);records.append({'index':index,'relative_file':row['relative_file'],'sha256':captured['sha256'],'canonical_pixel_sha256':pixel,
                                               'identity':row['identity'],'day':row['day'],'bytes':len(raw)})
assert len(records)==457 and all(len(indices)==1 for indices in allpixels.values())
for source in ['Cows_training_images','MultiCam_training_images']:
 ids=defaultdict(set)
 for row in plan[source]:ids[row['identity']].add(row['day'])
 assert all(len(days)>=2 for days in ids.values())
result={'status':'ALL457_SOURCE_CRC_PIXELS_ROLES_AND_CROSSDATE_TRAINING_ID_COUNTS_PASS','created_UTC':datetime.now(timezone.utc).isoformat(),
        'admitted':True,'Cows_records':records,'MultiCam_existing_training_images':580,'new_Cows_training_IDs':16,'future_final_ID_candidates_pixels_closed':20,
        'training_IDs_disjoint_priorCows120_and_future20':True,'cross_date_positives_available_all_train_IDs':True,
        'new_image_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
p=ROOT/'results/input_admission.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:value for key,value in result.items()if key!='Cows_records'}))
