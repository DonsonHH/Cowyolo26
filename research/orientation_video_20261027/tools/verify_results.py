"""Independent inverse coordinates, original regressions,12event replays."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,functools,hashlib,json,math
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def replay(rows,ticks,fps):
    states={};byframe=defaultdict(list);events=[]
    for row in rows:byframe[int(row['source_frame'])].append(row)
    for frame in ticks:
        positions={int(r['track_id']):float(r['axis_position']) for r in byframe.get(frame,[])}
        for tid,state in states.items():
            if tid not in positions:state['candidate']=None;state['streak']=0
        for tid,p in positions.items():
            if not 0<=p<=1:continue
            s=states.setdefault(tid,{'origin':None,'candidate':None,'streak':0,'last':-1e30})
            if frame/fps-s['last']>2:s.update(origin=None,candidate=None,streak=0)
            s['last']=frame/fps;zone='A' if p<.4 else 'B' if p>.6 else None
            if zone is None:s.update(candidate=None,streak=0);continue
            s['streak']=s['streak']+1 if zone==s['candidate'] else 1;s['candidate']=zone
            if s['streak']>=3 and s['origin']!=zone:
                if s['origin'] is not None:events.append({'time_s':frame/fps,'track_id':tid,'direction':s['origin']+'->'+zone,'source_frame':frame})
                s['origin']=zone
    return events

def matching(reference,predicted):
    # DP over prediction index and used reference mask. Independent of SciPy.
    n=len(reference);assert n==6
    @functools.lru_cache(None)
    def solve(j,mask):
        if j==len(predicted):return (0,0.,())
        best=solve(j+1,mask)
        for i,r in enumerate(reference):
            delta=abs(float(r['time_s'])-float(predicted[j]['time_s']))
            if mask&(1<<i) or delta>2:continue
            count,error,pairs=solve(j+1,mask|(1<<i))
            candidate=(count+1,error+delta,((i,j),)+pairs)
            if (candidate[0],-candidate[1])>(best[0],-best[1]):best=candidate
        return best
    _,_,pairs=solve(0,0)
    correct=sum(reference[i]['direction']==predicted[j]['direction'] for i,j in pairs)
    return {'TP':correct,'FP':len(predicted)-correct,'FN':len(reference)-correct,
            'temporally_matched':len(pairs),'wrong_direction_matches':len(pairs)-correct}


def read_csv(path):return list(csv.DictReader(path.open(encoding='utf-8',newline='')))


def normalise(rows):
    return [{k:(None if v is None or v=='' else int(v) if k in ['source_frame','frame','track_id'] else float(v))
             for k,v in row.items()} for row in rows]


def main():
    delivered=ROOT/'delivery';manifest=json.loads((delivered/'delivery_manifest.json').read_text(encoding='utf-8'))
    assert len({r['path'] for r in manifest})==len(manifest)
    for row in manifest:
        p=delivered/row['path'];assert p.resolve().is_relative_to(delivered.resolve())
        assert p.is_file() and p.stat().st_size==row['bytes'] and sha(p)==row['sha256']
    protocol_path=delivered/'protocol/video_rotation_v1.json';p=json.loads(protocol_path.read_text(encoding='utf-8'))
    assert sha(protocol_path)==sha(ROOT/'protocol/video_rotation_v1.json')
    frozen_path=delivered/'input/checkpoint_freeze.json';frozen=json.loads(frozen_path.read_text(encoding='utf-8'))
    assert sha(frozen_path)==p['source_weights_freeze_sha256']
    assert frozen['source_Toros_or_candidate_final_forward_before_freeze'] is False
    result_path=delivered/'results/inference';summary=json.loads((result_path/'summary.json').read_text(encoding='utf-8'))
    assert summary['status']=='SIX_VIDEO_ROTATION_CONDITIONS_COMPLETE_ORIGINAL_TRACES_REPRODUCED'
    assert summary['protocol_sha256']==sha(protocol_path) and summary['training_freeze_sha256']==sha(frozen_path)
    assert summary['new_training_updates']==0 and summary['source_count_accuracy'] is None
    assert [(r['seed'],r['orientation']) for r in summary['conditions']]==[(s,o) for s in [26,27,28] for o in ['original','clockwise90']]
    fixed=json.loads((result_path/'all_conditions_fixed_before_replay.json').read_text(encoding='utf-8'))
    assert fixed['protocol_sha256']==sha(protocol_path) and fixed['prior_weight_freeze_sha256']==sha(frozen_path)
    assert [(r['seed'],r['orientation']) for r in fixed['conditions']]==[(r['seed'],r['orientation']) for r in summary['conditions']]
    reference=json.loads((result_path/'toros_reference_events.json').read_text(encoding='utf-8'))
    old_reference=ROOT.parent/'cows2021_adaptation_20261027/delivery/results/inference/toros_reference_events.json'
    assert reference==json.loads(old_reference.read_text(encoding='utf-8')) and len(reference)==6
    smoke=json.loads((delivered/'results/smoke.json').read_text(encoding='utf-8'))
    nonempty=json.loads((delivered/'results/nonempty_seam_smoke.json').read_text(encoding='utf-8'))
    assert smoke['status']=='SYNTHETIC_NONEMPTY_EMPTY_RESULTS_AND_REAL_BYTE_TRACK_SEAM_CONTROLS_PASS'
    assert nonempty['status']=='REAL_NONEMPTY_NEURAL_BOXES_IN_BOTH_ORIENTATIONS_RESTORE_BEFORE_BYTE_TRACK'
    assert smoke['protocol_sha256']==nonempty['protocol_sha256']==sha(protocol_path)
    assert all(r['pretracker_boxes'] and r['posttracker_data'] for r in nonempty['records'])
    checks=[];coordinate_rows=0;seam_frames=0;maximum_subtraction_rounding=0.;original_regressions=0;overlay_count=0
    for condition in summary['conditions']:
        seed,orientation=condition['seed'],condition['orientation'];name=condition['name']
        prior=next(r for r in frozen['conditions'] if r['seed']==seed)
        assert condition['checkpoint_sha256']==prior['checkpoint_sha256']
        local_weight=ROOT.parent/f'cows2021_adaptation_20261027/delivery/results/training/seed{seed}/weights/last.pt'
        assert sha(local_weight)==prior['checkpoint_sha256']
        dest=result_path/name
        for scene in ['source','Toros']:
            native_H,native_W=(1440,2560) if scene=='source' else (1080,1920)
            fps=25 if scene=='source' else 30
            expected_frames=list(range(0,10874,5)) if scene=='source' else list(range(479))
            seam=json.loads((dest/f'{scene}_seam_checks.json').read_text(encoding='utf-8'))
            assert [r['frame'] for r in seam['checks']]==expected_frames
            seam_frames+=len(expected_frames)
            order=seam['callback_order']
            restore=next(i for i,r in enumerate(order) if r['name']=='restore_before_tracker' and r['module']=='rotation_seam')
            tracking=next(i for i,r in enumerate(order) if r['name']=='on_predict_postprocess_end' and r['module']=='ultralytics.trackers.track')
            assert restore<tracking and seam['detector_coordinate_restore_before_tracker'] is True
            for record in seam['checks']:
                assert record['native_coordinates_restored_before_tracker'] is True
                assert (record['native_H'],record['native_W'])==(native_H,native_W)
                assert (record['input_H'],record['input_W'])==((native_H,native_W) if orientation=='original' else (native_W,native_H))
            raw=read_csv(dest/f'{scene}_pretracker_boxes.csv');raw_count=Counter();rounding=defaultdict(float)
            for row in raw:
                f=int(row['frame']);assert f in expected_frames and float(row['time_s'])==f/fps
                points=[(float(row['input_x1']),float(row['input_y1'])),(float(row['input_x1']),float(row['input_y2'])),
                        (float(row['input_x2']),float(row['input_y1'])),(float(row['input_x2']),float(row['input_y2']))]
                if orientation=='clockwise90':points=[(v,native_H-u) for u,v in points]
                xx,yy=zip(*points);expected=[min(xx),min(yy),max(xx),max(yy)]
                actual=[float(row[k]) for k in ['x1','y1','x2','y2']]
                assert np.array_equal(np.asarray(expected,dtype=np.float32).astype(float),np.asarray(actual))
                error=max(abs(a-b) for a,b in zip(actual,expected))
                rounding[f]=max(rounding[f],error);maximum_subtraction_rounding=max(maximum_subtraction_rounding,error)
                assert all(math.isfinite(v) for v in actual) and actual[0]<=actual[2] and actual[1]<=actual[3]
                assert float(row['confidence'])>=.2
                raw_count[f]+=1;coordinate_rows+=1
            for row in seam['checks']:
                assert row['detector_boxes']==raw_count[row['frame']]
                assert row['max_float32_inverse_difference']==rounding[row['frame']]
            tracks=read_csv(dest/f'{scene}_tracks.csv')
            history=read_csv(dest/'source_warmup_tracks.csv') if scene=='source' else []
            for row in history+tracks:
                pos=((float(row['y1'])+float(row['y2']))/2/native_H if scene=='source'
                     else (float(row['x1'])+float(row['x2']))/2/native_W)
                assert float(row['axis_position'])==pos
                cross=((float(row['x1'])+float(row['x2']))/2/native_W if scene=='source'
                       else (float(row['y1'])+float(row['y2']))/2/native_H)
                assert (.34<cross<.75 if scene=='source' else .1<cross<.95)
            events=json.loads((dest/f'{scene}_events.json').read_text(encoding='utf-8'))
            actual_events=replay(history+tracks,expected_frames,fps)
            if scene=='source':actual_events=[e for e in actual_events if e['source_frame']>=8912]
            assert actual_events==events,(name,scene)
            if orientation=='original':
                baseline=delivered/'input/baseline'/f'seed{seed}'
                assert events==json.loads((baseline/f'{scene}_events.json').read_text(encoding='utf-8'))
                assert normalise(tracks)==normalise(read_csv(baseline/f'{scene}_tracks.csv'))
                if scene=='source':assert normalise(history)==normalise(read_csv(baseline/'source_warmup_tracks.csv'))
                original_regressions+=1
            record={'condition':name,'seed':seed,'orientation':orientation,'scene':scene,'events':len(events),
                    'native_coordinate_rows':len(raw),'pretracker_hook_frames':len(expected_frames),
                    'original_events_and_tracks_reproduced':orientation=='original'}
            scene_summary=json.loads((dest/f'{scene}_summary.json').read_text(encoding='utf-8'))
            assert scene_summary['tracker_and_counter_coordinate_system']=='original native camera'
            assert scene_summary['detector_input_orientation']==orientation
            assert scene_summary['detector_pretracker_boxes']==len(raw)
            assert scene_summary['events']==len(events)
            if scene=='Toros':
                metrics=matching(reference,events)
                assert all(condition['Toros_event_metrics'][k]==v for k,v in metrics.items())
                record.update(metrics)
                assert scene_summary['sampled_inference_frames']==479
            else:
                assert scene_summary['sampled_inference_frames']==2175 and scene_summary['rendered_frames']==1962
                assert scene_summary['source_output_frame_range']==[8912,10873]
            checks.append(record)
        for frame in [8912,9420,10873]:
            with Image.open(dest/f'source_f{frame}.jpg') as image:image.load();assert image.size==(1280,720)
            overlay_count+=1
    assert len(checks)==12 and original_regressions==6 and seam_frames==15924 and overlay_count==18
    result={'status':'INVERSE_COORDINATES_ORIGINAL_REGRESSIONS_AND_12_EVENT_REPLAYS_INDEPENDENTLY_VERIFIED',
            'protocol_sha256':sha(protocol_path),'delivery_files_verified':len(manifest),'conditions':checks,
            'pretracker_inverse_coordinate_rows_verified':coordinate_rows,'pretracker_hook_frames_verified':seam_frames,
            'maximum_double_to_float32_coordinate_rounding_pixels':maximum_subtraction_rounding,
            'all_original_event_and_track_regressions_passed':6,'overlay_full_decodes':18,
            'training_updates':0,'new_independent_source_count_accuracy_verified':False,
            'final_test_or_Z2_joint_execution_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/independent_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
