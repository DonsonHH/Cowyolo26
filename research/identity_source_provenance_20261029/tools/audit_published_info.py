from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    info=load(ROOT/'evidence/zip_metadata/info.json');records=[];keys=Counter();semantic=[];leaf_keys=Counter()
    def walk(value,path='$'):
        if isinstance(value,dict):
            keys.update(value.keys())
            if 'id' in value and str(value.get('type',''))!='Dataset' and 'hasPart' not in value and 'sha1' in value:
                records.append(value);leaf_keys.update(value.keys())
            for key,item in value.items():
                if any(t in key.lower() for t in ['timestamp','frame','crop','bbox','coord','identity']):semantic.append({'path':path,'key':key,'value_preview':str(item)[:150]})
                walk(item,path+'.'+key)
        elif isinstance(value,list):
            for i,item in enumerate(value):walk(item,path+f'[{i}]')
    walk(info);byid={r['id']:r for r in records};assert len(records)==len(byid)
    suffixes=Counter(Path(r['id']).suffix.lower() for r in records)
    assert suffixes['.jpg']==101329 and suffixes['.mp4']==137 and len(records)==101467
    assert semantic==[]
    gallery=load(PROJECT/'identity_training_20261026/delivery/results/study/feature_index.json')['evaluation_gallery'];checks=[]
    for r in gallery:
        name='2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/'+r['day']+'/'+r['identity']+'/'+r['source_filename']
        member=byid[name];file=PROJECT/'identity_training_20261026/delivery'/r['relative_path'];data=file.read_bytes()
        assert hashlib.sha1(data).hexdigest()==member['sha1'] and str(len(data))==member['extent']['@value']
        checks.append({'published_file_id':name,'published_SHA1':member['sha1'],'local_SHA256':hashlib.sha256(data).hexdigest(),
                       'published_fields':sorted(member),'source_frame_or_coordinates_present':False})
    sourceid='2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera1/2023Aug14/2023-08-14T12-54-48.mp4'
    member=byid[sourceid];file=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4'
    assert hashlib.sha1(file.read_bytes()).hexdigest()==member['sha1'] and str(file.stat().st_size)==member['extent']['@value']
    result={'status':'PUBLISHED_INFO_JSON_ALL101467_FILE_RECORDS_CHECKED_AND30_GALLERY_PLUS_RAW_VIDEO_SHA1_VERIFIED',
       'info_json_sha256':hashlib.sha256((ROOT/'evidence/zip_metadata/info.json').read_bytes()).hexdigest(),
       'top_level_fields':list(info),'file_record_count':len(records),'file_suffix_counts':dict(suffixes),'leaf_field_counts':dict(leaf_keys),
       'all_object_field_counts':dict(keys),'explicit_frame_timestamp_crop_coordinate_identity_field_hits':semantic,
       'gallery_checks':checks,'raw_video_published_SHA1':member['sha1'],'raw_video_matches_published_SHA1':True,
       'explicit_published_image_to_raw_frame_mapping_found':False,'published_metadata_is_file_catalog_not_tracklet_CSV':True,
       'whole_goal_complete':False}
    path=ROOT/'results/published_info_schema_audit.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['gallery_checks','all_object_field_counts']}))
if __name__=='__main__':main()
