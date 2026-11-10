"""No-inference shadow replay: hold B's actual observation times fixed and mask crops."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def replay(folder,mask_local):
    from counting.tracking import TrackingSession
    folder=Path(folder)
    summary=json.loads((folder/'summary.json').read_bytes())
    assert summary['status']=='COMPLETED_UNSCORED' and not summary['software_fixture_only']
    rows=[json.loads(line) for line in (folder/'frames.jsonl').read_bytes().splitlines()]
    tracking=TrackingSession(summary['config'],*summary['source_size'],5.,
                             summary['session_id']+('_mask' if mask_local else '_use'))
    counts={'IN':0,'OUT':0,'NET':0};events=[];previous=-1
    local_frames=0
    for row in rows:
        assert row['frame0']>previous;previous=row['frame0']
        assert all(row[k]==summary[k] for k in ('video_id','session_id','run_id'))
        local_frames+=int(row['local_record'] is not None)
        detections=np.asarray(row['base_detections' if mask_local else 'detections'],
                              np.float32).reshape(-1,6)
        tracks,emitted,uncertain=tracking.update(row['frame0'],row['time_s'],detections)
        for event in emitted:
            counts[event['kind']]+=1;events.append(event)
        counts['NET']=counts['IN']-counts['OUT']
        if not mask_local:assert counts==row['counts'],(row['frame0'],counts,row['counts'])
    if not mask_local:assert counts==summary['counts']
    return {'counts':counts,'observed_images':len(rows),'frames_with_local_attempt':local_frames,
            'mask_local_measurements':mask_local,'events':events,'new_model_forwards':0}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--case',action='append',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--expected-tracking-source',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    args=parser.parse_args()
    expected=json.loads(args.expected_tracking_source.read_bytes())
    for name,digest in expected.items():assert sha(args.runtime/name)==digest,name
    sys.path.insert(0,str(args.runtime))
    result={'status':'COMPLETED_SHADOW_REPLAY','new_model_forwards':0,
            'runtime_metrics_valid':False,'original_scheduler_reexecuted':False,
            'counterfactual_scheduler_claim':False,
            'scope':'Use/mask on the same recorded B observation images/times; shadow state never feeds proposals or real capture.',
            'tracking_source_sha256':expected,'cases':[]}
    for case in args.case:
        summary=json.loads((case/'summary.json').read_bytes())
        result['cases'].append({'case':str(case),'policy':summary['policy'],
            'original_run_id':summary['run_id'],'source_video_sha256':summary['video_sha256'],
            'input_sha256':{n:sha(case/n) for n in ('summary.json','frames.jsonl','events.jsonl')},
            'use':replay(case,False),'mask':replay(case,True)})
    with args.output.open('x') as out:json.dump(result,out,indent=2);out.write('\n')
    print(json.dumps({'status':result['status'],'new_model_forwards':0,'cases':[
        {'policy':c['policy'],'use':c['use']['counts'],'mask':c['mask']['counts']}
        for c in result['cases']]},indent=2))
if __name__=='__main__':main()
