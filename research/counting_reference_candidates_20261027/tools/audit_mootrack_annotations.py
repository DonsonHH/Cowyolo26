"""Inspect public annotation bytes without video, predictions or author code execution."""
from pathlib import Path
from collections import Counter,defaultdict
import configparser,csv,hashlib,io,json,math,zipfile

ROOT=Path(__file__).resolve().parents[1]


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    archive=ROOT/'catalog/MooTrack360_TrackEval_evaluation_code.zip'
    data=archive.read_bytes()
    assert len(data)==23441568 and hashlib.md5(data).hexdigest()=='907533e4bc6398c7761b073be3fb4019'
    with zipfile.ZipFile(archive) as z:
        gt_names=[i.filename for i in z.infolist() if '/data/gt/' in i.filename and i.filename.endswith('/gt/gt.txt')]
        ini_names=[i.filename for i in z.infolist() if '/data/gt/' in i.filename and i.filename.endswith('/seqinfo.ini')]
        assert len(gt_names)==len(ini_names)==1
        raw=z.read(gt_names[0]);ini=z.read(ini_names[0])
    config=configparser.ConfigParser();config.read_string(ini.decode('utf-8-sig'))
    sequence=dict(config['Sequence'])
    width,height=int(sequence['imwidth']),int(sequence['imheight'])
    declared_frames,fps=int(sequence['seqlength']),float(sequence['framerate'])
    rows=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))));assert rows
    columns=Counter(len(r) for r in rows)
    frames=Counter();tracks=defaultdict(list);pairs=Counter();bounds=[];invalid=[];trailing=Counter();confidence=Counter()
    for number,row in enumerate(rows,1):
        values=list(map(float,row));assert len(values)==10 and all(math.isfinite(v) for v in values)
        frame,tid,x,y,w,h,score,*unknown=values
        assert frame==int(frame) and tid==int(tid)
        frame,tid=int(frame),int(tid)
        frames[frame]+=1;tracks[tid].append(frame);pairs[(frame,tid)]+=1
        confidence[str(score)]+=1;trailing[str(unknown)]+=1
        if w<=0 or h<=0:invalid.append(number)
        if min(x,y)<0 or x+w>width or y+h>height:bounds.append(number)
    repeated=[{'frame':k[0],'track_id':k[1],'rows':v} for k,v in pairs.items() if v>1]
    track_summary=[{'track_id':tid,'first_frame':min(v),'last_frame':max(v),'labelled_frames':len(v),
                    'missing_integer_frames_inside_span':max(v)-min(v)+1-len(set(v))}
                   for tid,v in sorted(tracks.items())]
    result={'status':'PUBLISHED_MOOTRACK_GT_METADATA_AUDITED_VIDEO_ALIGNMENT_NOT_VERIFIED',
            'source_url':'https://zenodo.org/records/20287681',
            'archive_bytes':len(data),'archive_sha256':sha(data),'GT_path_in_archive':gt_names[0],
            'GT_bytes':len(raw),'GT_sha256':sha(raw),'sequence_metadata':sequence,'seqinfo_sha256':sha(ini),
            'annotation_rows':len(rows),'column_counts':dict(columns),'track_IDs':len(tracks),
            'minimum_frame':min(frames),'maximum_frame':max(frames),'annotated_distinct_frames':len(frames),
            'declared_seq_length':declared_frames,'declared_fps':fps,
            'declared_sequence_seconds_if_fps_correct':declared_frames/fps,
            'labelled_frame_span_seconds_if_fps_correct':(max(frames)-min(frames)+1)/fps,
            'label_frames_exceed_declared_length':max(frames)>declared_frames,
            'dimensions':[width,height],'nonpositive_boxes':len(invalid),'boxes_outside_declared_image':len(bounds),
            'duplicate_frame_track_ID_pairs':repeated,'confidence_column_distribution':dict(confidence),
            'last_three_column_values_uninterpreted':dict(trailing),
            'last_three_columns_not_assumed_class_or_visibility':True,
            'track_summary':track_summary,'official_one_hour_description_alignment_verified':False,
            'source_video_native_frames_or_burned_overlays_checked':False,
            'bidirectional_channel_passages_verified':False,'final_test_eligibility_certified':False,
            'new_model_prediction_or_training':False,'whole_goal_complete':False}
    out=ROOT/'results';out.mkdir(exist_ok=True)
    target=out/'MooTrack360_annotation_audit.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['track_summary','duplicate_frame_track_ID_pairs']}),flush=True)


if __name__=='__main__':main()
