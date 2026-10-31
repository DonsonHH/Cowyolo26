from pathlib import Path
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
case=load(ROOT/'results/S192_rot90_seed26/iou05/case.json');events={r['track_id']:r for r in load(ROOT/'input/reference_events.json')}
refs=defaultdict(dict)
for row in load(ROOT/'input/reference_boxes.json'):refs[row['reference_track_id']][row['frame0']]=row
choices=[]
for track in case['tracks']:
    if track['actual_direct_corresponding_down_events']:continue
    tid=track['reference_track_id'];runs=track['longest_stable_region_runs']['presence_using_reference_center']
    zone='A' if runs['A']<3 else 'B';end=None;run=[]
    for frame,row in sorted(refs[tid].items()):
        position=row['axis_position'];eligible=position<.4 if zone=='A' else position>.6
        if not eligible:run=[];continue
        if run and frame!=run[-1]+5:run=[]
        run.append(frame)
        if len(run)>=3:end=frame;break
    assert end is not None
    frames=[end-10,end-5,end];assert all(frame in refs[tid] and 8912<=frame<=10873 for frame in frames)
    choices.append({'reference_track_id':tid,'event_frame0':events[tid]['frame0'],'zone':zone,'frames':frames,
       'selection':'First3consecutivebaseline-referenceobservationsinthezonewithinsufficientraw-presencestability;chosenmechanicallybeforepixelinspection.',
       'raw_presence_longest_A':runs['A'],'raw_presence_longest_B':runs['B']})
assert len(choices)==6
frames=sorted({frame for row in choices for frame in row['frames']});assert len(frames)<=18
source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';assert sha(source)=='5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'
protocol={'status':'FROZEN_BEFORE_NEW_CASE_PIXEL_INSPECTION','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'primary_model':'S192_rot90_seed26','primary_case_SHA256':sha(ROOT/'results/S192_rot90_seed26/iou05/case.json'),
 'source_sha256':sha(source),'choices':choices,'unique_export_frames':frames,'count':len(frames),
 'source_export_scope':[8912,10873],'annotations_are_model_outputs_not_GT':True,'new_network_forwards':0,'whole_goal_complete':False}
file=ROOT/'protocol/visual_v1.json';assert not file.exists();file.write_text(json.dumps(protocol,indent=2)+'\n')
out=ROOT/'media';out.mkdir(exist_ok=False);raw=out/'native';raw.mkdir(exist_ok=False)
expression='+'.join('eq(n\\,'+str(frame)+')' for frame in frames)
command=['ffmpeg','-v','error','-threads','2','-i',str(source),'-vf','select='+expression,'-fps_mode','vfr',str(raw/'source_%03d.png')]
(ROOT/'results/visual_extract_command.json').write_text(json.dumps({'command':command,'frames':frames,'source_sha256':sha(source)},indent=2)+'\n')
result=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);assert result.returncode==0,result.stderr.decode(errors='replace')
files=sorted(raw.glob('source_*.png'));assert len(files)==len(frames)
record={'status':'FIXED_MODEL_DIAGNOSTIC_SOURCE_FRAMES_EXTRACTED_ONLY_WITHIN_USER_SCOPE',
 'frames':[{'source_frame0':frame,'file':str(file.resolve()),'sha256':sha(file)} for frame,file in zip(frames,files)],
 'new_reference_labels':0,'new_network_forwards':0,'whole_goal_complete':False}
file=ROOT/'results/native_frame_manifest.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'selected_cases':6,'unique_source_frames':len(frames),'exported':len(files)}))
