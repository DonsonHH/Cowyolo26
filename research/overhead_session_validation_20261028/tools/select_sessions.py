"""Select new ordinary-overhead video sessions from metadata, before image inspection."""
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
from collections import Counter
import hashlib,json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse_time(name):
    day,clock=name.split('_');parts=[int(x) for x in clock.split('-')]
    return datetime.fromisoformat(day).replace(hour=parts[0],minute=parts[1],second=parts[2])

def main():
    inv_path=ROOT/'evidence/source_inventory.json';inv=json.loads(inv_path.read_text(encoding='utf-8'))
    labels_path=PROJECT/'cows2021_adaptation_20261027/delivery/results/labels_v1/prepared_image_label_manifest.json'
    labels=json.loads(labels_path.read_text(encoding='utf-8'));times=set()
    for r in labels:
        tail=r['original_filename'].split('_')[-2:];times.add(parse_time('_'.join(tail)))
    existing={r['sequence'] for r in inv['existing_local_server_samples']};allrows=[]
    for url in inv['published_video_directory_links']:
        name=unquote(url.rstrip('/').split('/')[-1]);t=parse_time(name)
        close=sorted(s for s in times if abs((s-t).total_seconds())<=10)
        reasons=[]
        if name in existing:reasons.append('previously_used_video')
        if t.date().isoformat()=='2020-03-11':reasons.append('reserved_final_date_not_opened')
        if close:reasons.append('within_10s_of_existing_development_image_session')
        allrows.append({'sequence':name,'url':url+'RGB.avi','capture_timestamp':t.isoformat(),
                        'nearby_development_timestamps':[x.isoformat() for x in close],'exclusion_reasons':reasons})
    eligible=sorted([r for r in allrows if not r['exclusion_reasons']],key=lambda r:r['capture_timestamp'])
    assert len(eligible)>=4,'Do not weaken source-disjoint rules silently'
    chosen=[eligible[i] for i in sorted(set([0,(len(eligible)-1)//3,2*(len(eligible)-1)//3,len(eligible)-1]))]
    out=ROOT/'protocol';out.mkdir(parents=True,exist_ok=False)
    p={'status':'FOUR_METADATA_SELECTED_NONFINAL_DATE_VIDEO_SESSIONS_FROZEN','selection_before_new_pixel_or_model_inspection':True,
       'source_inventory_sha256':sha(inv_path),'actual_prepared_image_label_manifest_sha256':sha(labels_path),
       'prepared_image_rows':len(labels),'distinct_prepared_image_source_timestamps':len(times),
       'selection_rule':'Exclude existing videos, final reserved 2020-03-11 and sessions within 10 s of any actual prepared development-image timestamp; select chronological quantile indices 0, floor((n-1)/3), floor(2(n-1)/3), n-1.',
       'all_directory_rows':len(allrows),'directory_rows_by_day':dict(Counter(r['capture_timestamp'][:10] for r in allrows)),
       'eligible_sessions':len(eligible),'eligible_by_day':dict(Counter(r['capture_timestamp'][:10] for r in eligible)),
       'selected':chosen,'all_candidates':allrows,'maximum_each_video_bytes':100*1024*1024,'maximum_total_video_bytes':400*1024*1024,
       'weights_frozen':'human_count_confirmation_20261028/results/frozen_development_candidate.json',
       'current_source_12_reference_preserved':True,'geometric_camera_calibration_to_be_frozen_before_inference':True,
       'timestamp_disjoint_is_not_proof_of_pixel_independence':True,'per_event_reference_present':False,
       'new_training_updates':0,'whole_goal_complete':False}
    (out/'sessions_v1.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in p.items() if k in ['status','prepared_image_rows','distinct_prepared_image_source_timestamps','all_directory_rows','directory_rows_by_day','eligible_sessions','eligible_by_day','selected']}),flush=True)

if __name__=='__main__':main()
