"""ROI-preserving ID controls and descriptive spatial support of frozen event matches."""
from pathlib import Path
from collections import defaultdict
import contextlib,csv,io,json,runpy

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent


def main():
    with contextlib.redirect_stdout(io.StringIO()):
        independent=runpy.run_path(str(ROOT/'tools/verify_new_diagnosis.py'))
    associate=independent['associate'];events=independent['events'];centre=independent['centre'];load=independent['load'];iou=independent['iou']
    gt=independent['gt'];summary=independent['summary']
    controls=[];runs=[]
    for seed in [26,27,28]:
        model=f'epoch20_seed{seed}'
        post=load(ROOT/f'delivery/results/capture/{model}/post_tracker_boxes.csv')
        raw=load(ROOT/f'delivery/results/capture/{model}/raw_detector_boxes.csv')
        for threshold in [.5,.3]:
            strict_frames=defaultdict(dict)
            point_frames={kind:defaultdict(dict) for kind in ['raw','post']}
            for f in range(479):
                for kind,prediction in [('raw',raw[f]),('post',post[f])]:
                    for i,j in associate(gt[f],prediction,threshold):
                        g,p=gt[f][i],prediction[j];x,y=centre(p['box'])
                        if not .1<y<.95:continue
                        point_frames[kind][g['id']][f]=x
                        if kind=='post' and p['id'] is not None:strict_frames[f][g['id']]=x
            output=events(strict_frames)
            controls.append({'model':model,'association_iou':threshold,'original_ROI_preserved':True,
                             'condition':'post_boxes_with_actual_ID_then_reference_ID','events':output,'event_count':len(output)})
            if threshold==.5:
                for rid in [1,14,7,16,22,17]:
                    for kind in ['raw','post']:
                        samples=point_frames[kind][rid];row={'model':model,'reference_id':rid,'kind':kind,'matched_ROI_frames':len(samples)}
                        for zone in ['A','B']:
                            fs=sorted(f for f,x in samples.items() if x<.4) if zone=='A' else sorted(f for f,x in samples.items() if x>.6)
                            best=streak=0;previous=None
                            for f in fs:
                                streak=streak+1 if previous is not None and f==previous+1 else 1;best=max(best,streak);previous=f
                            row['max_consecutive_'+zone]=best
                        runs.append(row)
    old=json.loads((ROOT/'delivery/results/layers/additional_controls.json').read_text(encoding='utf-8'))
    differences=[]
    for row in controls:
        prior=next(r for r in old['id_presence_controls'] if r['model']==row['model'] and r['association_iou']==row['association_iou'])
        canonical=lambda es:sorted([(e['frame'],e['track_id'],e['direction']) for e in es])
        if canonical(prior['events'])!=canonical(row['events']):differences.append({'model':row['model'],'iou':row['association_iou'],'original_unfiltered_events':prior['events'],'strict_events':row['events']})
    inference=json.loads((BASE/'detector_training_20261027/delivery/results/inference/summary.json').read_text(encoding='utf-8'))
    ref=json.loads((BASE/'detector_training_20261027/delivery/results/inference/toros_reference_events.json').read_text(encoding='utf-8'))
    spatial=[]
    for condition in inference['conditions']:
        model=condition['name']
        if model in ['generic','pilot']:
            path=BASE/f'phase3_diagnosis_20261026/inputs/{model}_Toros_detections.csv'
            boxes=load(path)
        else:boxes=load(ROOT/f'delivery/results/capture/{model}/post_tracker_boxes.csv')
        predictions=json.loads((BASE/f'detector_training_20261027/delivery/results/inference/{model}/Toros_events.json').read_text(encoding='utf-8'))
        for pair in condition['Toros_event_metrics']['pairs']:
            g=ref[pair['reference_index']];p=predictions[pair['prediction_index']]
            ef=p['source_frame'];observations=[]
            for f in range(max(0,ef-15),min(479,ef+16)):
                a=[r for r in gt[f] if r['id']==g['track_id']]
                b=[r for r in boxes[f] if r['id']==p['track_id']]
                if a and b:
                    assert len(a)==len(b)==1
                    observations.append({'frame':f,'iou':iou(a[0]['box'],b[0]['box'])})
            spatial.append({'model':model,'reference_id':g['track_id'],'reference_event_frame':g['frame'],
                            'predicted_track_id':p['track_id'],'predicted_event_frame':ef,
                            'frozen_direction_correct':pair['direction_correct'],
                            'same_frame_pair_observations':len(observations),'max_same_frame_iou':max((r['iou'] for r in observations),default=None),
                            'frames_at_iou05':sum(r['iou']>=.5 for r in observations),'frames_at_iou03':sum(r['iou']>=.3 for r in observations),
                            'observations':observations})
    result={'status':'STRICT_ROI_CONTROLS_AND_FROZEN_MATCH_SPATIAL_DESCRIPTIONS_COMPLETE','strict_ID_presence_conditions':controls,
            'ROI_change_effects_vs_archived_control':differences,'stable_region_runs_primary_iou05':runs,
            'frozen_actual_temporal_matches_spatial_evidence':spatial,'frozen_TP_FP_FN_changed':False,
            'scope':'Controls/geometry descriptions only; event matching remains frozen, source observations are nonblind development material'}
    target=ROOT/'results/review_controls.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'strict_ID_event_counts':[(r['model'],r['association_iou'],r['event_count']) for r in controls],
                      'ROI_changes':len(differences),'spatial_pairs':len(spatial),
                      'pairs_without_IoU05_support':[{k:r[k] for k in ['model','reference_id','predicted_track_id','max_same_frame_iou']} for r in spatial if not r['frames_at_iou05']]}),flush=True)


if __name__=='__main__':main()
