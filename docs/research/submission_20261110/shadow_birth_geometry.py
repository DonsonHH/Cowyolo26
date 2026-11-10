"""Exploratory CPU-only birth geometry control on the fixed recorded B streams."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
parser=argparse.ArgumentParser()
parser.add_argument('--runtime',type=Path,required=True)
parser.add_argument('--case',action='append',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
a=parser.parse_args();sys.path.insert(0,str(a.runtime))
from counting.tracking import TrackingSession
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
result={'status':'EXPLORATORY_FIXED_OUTPUT_GEOMETRY_CONTROL','new_model_forwards':0,
 'proposal_schedule_reexecuted':False,'hardware_accuracy_result':False,
 'scope':'Only birth-refinement coordinates are restored to the actually measured global seed; verified local score is retained. Endpoint geometry unchanged. Fixed recorded proposals are a shadow control, not a full policy rerun.',
 'cases':[]}
for case in a.case:
    s=json.loads((case/'summary.json').read_bytes())
    assert s['status']=='COMPLETED_UNSCORED' and s['policy']=='conditional_local_pair'
    rows=[json.loads(x) for x in (case/'frames.jsonl').read_bytes().splitlines()]
    t=TrackingSession(s['config'],*s['source_size'],5.,s['session_id']+'_birth_geometry_shadow')
    count={'IN':0,'OUT':0,'NET':0};changed=[];events=[]
    for row in rows:
        detections=np.array(row['detections'],np.float32).reshape(-1,6)
        record=row['local_record']
        if record and record['kind']=='birth' and record['accepted_detection'] is not None:
            index=record['proposal']['seed_index']
            base=np.array(row['base_detections'],np.float32).reshape(-1,6)
            assert len(base)==len(detections) and index<len(base)
            before=detections[index].copy();detections[index,:4]=base[index,:4]
            changed.append({'frame0':row['frame0'],'global_seed':base[index].tolist(),
                            'selected_local':before.tolist(),'fused':detections[index].tolist()})
        _,emitted,_=t.update(row['frame0'],row['time_s'],detections)
        for e in emitted:count[e['kind']]+=1;events.append(e)
        count['NET']=count['IN']-count['OUT']
    result['cases'].append({'case':str(case),'run_id':s['run_id'],'video_id':s['video_id'],
      'original_counts':s['counts'],'birth_confidence_only_counts':count,
      'changed_birth_measurements':changed,'shadow_events':events,
      'input_sha256':{n:sha(case/n) for n in ['summary.json','frames.jsonl','events.jsonl']}})
with a.output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
print(json.dumps([{'case':c['case'],'original':c['original_counts'],'new':c['birth_confidence_only_counts'],
                   'changed_births':len(c['changed_birth_measurements'])} for c in result['cases']],indent=2))
