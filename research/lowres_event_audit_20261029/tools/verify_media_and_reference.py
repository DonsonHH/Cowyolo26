from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
from PIL import Image
import json,hashlib,subprocess,sys,importlib.util,gzip
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('independent_reference_scanner',PROJECT/'long_video_fixed_replay_20261029/tools/verify_delivery.py');m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
reference=defaultdict(dict)
for r in load(ROOT/'input/reference_boxes.json'):reference[r['frame0']][str(r['reference_track_id'])]=r['axis_position']
obs=[{'frame0':frame,'time_s':frame/25,'confirmed_positions':reference[frame],'confirmed_IDs':sorted(int(k) for k in reference[frame])} for frame in range(0,10874,5)]
events,_=m.batch_events(obs,False);assert events==load(ROOT/'input/reference_events.json')
source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';protocol=load(ROOT/'protocol/visual_v1.json');native=load(ROOT/'results/native_frame_manifest.json');media=load(ROOT/'results/media_manifest.json')
assert sha(source)==protocol['source_sha256'] and len(native['frames'])==18 and len(media['pages'])==6
checks=[]
for row in native['frames']:
    frame=row['source_frame0'];assert 8912<=frame<=10873
    # Seek by timestamp instead of the extraction pass's frame-number select.
    command=['ffmpeg','-v','error','-threads','2','-ss',format(frame/25,'.8f'),'-i',str(source),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True);assert len(r.stdout)==1440*2560*3
    with Image.open(row['file']) as image:actual=np.asarray(image.convert('RGB'))
    assert actual.shape==(1440,2560,3) and actual.tobytes()==r.stdout and sha(row['file'])==row['sha256']
    checks.append({'source_frame0':frame,'timestamp_seek_seconds':frame/25,'RGB_pixel_sha256':hashlib.sha256(r.stdout).hexdigest(),'independent_timestamp_seek_matches_frame_select_exact':True})
cache=next(r for r in load(ROOT/'protocol/audit_v1.json')['caches'] if r['condition']=='S192_rot90_seed26')
raw={r['frame0']:r['predictions'] for r in json.loads(gzip.decompress(Path(cache['raw_file']).read_bytes()))};panels=0
for row in media['pages']:
    path=Path(row['path']);assert sha(path)==row['sha256']
    with Image.open(path) as image:image.load();assert image.size==(1920,900)
    choice=next(c for c in protocol['choices'] if c['reference_track_id']==row['reference_track_id'])
    assert [c['source_frame0'] for c in row['columns']]==choice['frames']
    for column in row['columns']:
        frame=column['source_frame0'];assert column['raw_boxes']==[r['xyxy'] for r in raw[frame]]
        x0,y0,x1,y1=column['detail_crop_box'];assert 0<=x0<x1<=2560 and 0<=y0<y1<=1440;panels+=2
assert panels==36
files=[PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json',PROJECT/'confirmation_handoff_20261028/delivery/results/replay_v2/seed26/source_tracks.csv',
 PROJECT/'confirmation_handoff_20261028/delivery/results/replay_v2/seed26/observations.json',PROJECT/'confirmation_handoff_20261028/delivery/results/replay_v2/seed26/handoff_events.json',
 PROJECT/'counting_recovery_20261028/delivery/results/replay_v2/full640_5hz_seed26/pretracker_boxes.csv']
result={'status':'ALL12_REFERENCE_EVENTS_AND18_TIMESTAMP_SEEKS36_PANEL_METADATA_VERIFIED','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'reference_self_events_independently_recomputed':12,'reference_is_independent_GT':False,'source_sha256':sha(source),
 'native_source_frame_pixel_checks':checks,'all18_frames_within_user_scope':True,'figure_count':6,'image_panels':panels,
 'source_records':[{'path':str(f.resolve()),'sha256':sha(f),'bytes':f.stat().st_size} for f in files],
 'new_model_forwards':0,'new_reference_labels':0,'whole_goal_complete':False}
file=ROOT/'results/media_and_reference_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['native_source_frame_pixel_checks','source_records']}))
