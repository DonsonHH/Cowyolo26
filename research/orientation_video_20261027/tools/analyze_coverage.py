"""Frame-level detector/tracker output coverage, never a recall estimate."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json

ROOT=Path(__file__).resolve().parents[1]


def read(path):return list(csv.DictReader(path.open(encoding='utf-8',newline='')))


def main():
    root=ROOT/'delivery/results/inference'
    summary=json.loads((root/'summary.json').read_text(encoding='utf-8'))
    assert summary['status']=='SIX_VIDEO_ROTATION_CONDITIONS_COMPLETE_ORIGINAL_TRACES_REPRODUCED'
    result=[]
    for condition in summary['conditions']:
        folder=root/condition['name']
        for scene in ['source','Toros']:
            width,height=(2560,1440) if scene=='source' else (1920,1080)
            sample_frames=set(range(8915,10874,5)) if scene=='source' else set(range(479))
            assert len(sample_frames)==(392 if scene=='source' else 479)
            raw=read(folder/f'{scene}_pretracker_boxes.csv')
            def in_roi(row):
                frame=int(row['frame'])
                cross=((float(row['x1'])+float(row['x2']))/2/width if scene=='source'
                       else (float(row['y1'])+float(row['y2']))/2/height)
                return frame in sample_frames and (.34<cross<.75 if scene=='source' else .1<cross<.95)
            raw_roi=[r for r in raw if in_roi(r)]
            raw_frames={int(r['frame']) for r in raw_roi}
            tracks=read(folder/f'{scene}_tracks.csv')
            assert {int(r['source_frame']) for r in tracks}.issubset(sample_frames)
            tracked_frames={int(r['source_frame']) for r in tracks}
            events=json.loads((folder/f'{scene}_events.json').read_text(encoding='utf-8'))
            row={'condition':condition['name'],'seed':condition['seed'],'orientation':condition['orientation'],
                 'scene':scene,'sampled_frames_in_scored_scope':len(sample_frames),
                 'pretracker_ROI_box_rows':len(raw_roi),'pretracker_ROI_frames':len(raw_frames),
                 'tracked_ROI_rows':len(tracks),'tracked_ROI_frames':len(tracked_frames),
                 'raw_ROI_present_but_no_ROI_track_frames':len(raw_frames-tracked_frames),
                 'frames_without_pretracker_ROI_candidates':len(sample_frames-raw_frames),
                 'unique_ROI_track_IDs':len({r['track_id'] for r in tracks}),
                 'predicted_A_to_B':sum(e['direction']=='A->B' for e in events),
                 'predicted_B_to_A':sum(e['direction']=='B->A' for e in events)}
            if scene=='Toros':row['known_diagnostic_TP_FP_FN']={k:condition['Toros_event_metrics'][k] for k in ['TP','FP','FN']}
            result.append(row)
    output={'status':'ALL12_NATIVE_COORDINATE_RAW_AND_TRACKED_OUTPUT_COVERAGES_COMPUTED',
            'source_inference_summary_sha256':hashlib.sha256((root/'summary.json').read_bytes()).hexdigest(),
            'records':result,'coverage_is_output_not_detection_recall_or_event_accuracy':True,
            'source_independent_truth_received':False,'new_model_forward_or_training':False,
            'whole_goal_complete':False}
    path=ROOT/'results/output_coverage.json';assert not path.exists();path.write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output),flush=True)


if __name__=='__main__':main()
