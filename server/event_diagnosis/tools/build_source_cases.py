"""Native source snapshots and model overlays for fixed prediction disagreements."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os
import cv2
from PIL import Image,ImageDraw

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'event_diagnosis'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    cv2.setNumThreads(2)
    p=json.loads((ROOT/'protocol/event_diagnosis_v1.json').read_text())
    OUT=ROOT/'results/source_cases';OUT.mkdir(parents=True,exist_ok=False)
    (OUT/'native').mkdir();(OUT/'overlays').mkdir()
    models=['pilot']+[r['name'] for r in p['models']]
    events={};tracks={}
    for name in models:
        dest=PROJECT/f'detector_training/results/inference/{name}'
        events[name]=json.loads((dest/'source_events.json').read_text())
        by_frame=defaultdict(list)
        for row in csv.DictReader((dest/'source_tracks.csv').open()):by_frame[int(row['source_frame'])].append(row)
        tracks[name]=by_frame
    selected=sorted({centre+offset for centre in p['source_disagreement_centres'] for offset in p['source_review_offsets_frames']})
    assert len(selected)==20 and all(8912<=f<=10873 and f%5==0 for f in selected)
    source=PROJECT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4';assert sha(source)==p['source_sha256']
    cap=cv2.VideoCapture(str(source));assert (cap.get(5),int(cap.get(3)),int(cap.get(4)))==(25.,2560,1440)
    frames=[]
    for f in range(max(selected)+1):
        ok,image=cap.read();assert ok,f
        if f not in selected:continue
        assert round(cap.get(cv2.CAP_PROP_POS_FRAMES))==f+1
        native=OUT/'native'/f'f{f}.jpg'
        assert cv2.imwrite(str(native),image,[cv2.IMWRITE_JPEG_QUALITY,95])
        overlays=[]
        for name in models:
            view=cv2.resize(image,(1280,720),interpolation=cv2.INTER_AREA)
            for x in [.34,.75]:cv2.line(view,(round(x*1280),0),(round(x*1280),719),(0,177,255),2)
            for y in [.4,.6]:cv2.line(view,(round(.34*1280),round(y*720)),(round(.75*1280),round(y*720)),(0,177,255),2)
            for row in tracks[name][f]:
                x1,y1,x2,y2=[round(float(row[k])/2) for k in ['x1','y1','x2','y2']]
                cv2.rectangle(view,(x1,y1),(x2,y2),(112,237,149),2)
                cv2.putText(view,f'track {row["track_id"]} {float(row["confidence"]):.2f}',(x1,max(60,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.65,(112,237,149),2)
            cv2.rectangle(view,(0,0),(1280,42),(18,24,28),-1)
            cv2.putText(view,f'{name} | source frame{f} ({f/25:.2f}s)',(20,29),cv2.FONT_HERSHEY_SIMPLEX,.8,(240,242,240),2)
            target=OUT/'overlays'/f'{name}_f{f}.jpg'
            assert cv2.imwrite(str(target),view,[cv2.IMWRITE_JPEG_QUALITY,92])
            overlays.append({'model':name,'path':str(target.relative_to(OUT)),'sha256':sha(target),
                             'tracks':tracks[name][f],'events_at_this_frame':[e for e in events[name] if e['source_frame']==f]})
        frames.append({'source_frame':f,'time_s':f/25,'decoded_pixel_bgr_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
                       'native_jpeg':str(native.relative_to(OUT)),'native_jpeg_sha256':sha(native),'native_size':[2560,1440],
                       'overlays':overlays})
    cap.release();assert len(frames)==20
    cases=[]
    for index,centre in enumerate(p['source_disagreement_centres'],1):
        selected_frames=[centre+offset for offset in p['source_review_offsets_frames']]
        rows=[next(r for r in frames if r['source_frame']==f) for f in selected_frames]
        window_events={name:[e for e in values if centre-50<=e['source_frame']<=centre+50] for name,values in events.items()}
        cases.append({'case_id':f'case{index}','centre_source_frame':centre,'centre_time_s':centre/25,
                      'frames':selected_frames,'predicted_events_in_4second_window':window_events,
                      'reference_status':'PREDICTION_DISAGREEMENT_REVIEW_ONLY_NO_GROUND_TRUTH'})
        sheet=Image.new('RGB',(4*480,5*288),(20,26,30));draw=ImageDraw.Draw(sheet)
        for row_index,row in enumerate(rows):
            for col,overlay in enumerate(row['overlays']):
                with Image.open(OUT/overlay['path']) as im:sheet.paste(im.convert('RGB').resize((480,270)),(col*480,row_index*288))
        sheet.save(OUT/f'case{index}_contact.jpg',quality=94)
    output={'status':'TWENTY_NATIVE_SOURCE_FRAMES_AND_80_OVERLAYS_PREPARED','job_id':os.environ['SLURM_JOB_ID'],
            'source_sha256':sha(source),'frame_numbering':'Original zero-based25fps, sequential OpenCV decode from0',
            'source_scope':[8912,10873],'models':models,'cases':cases,'frames':frames,
            'human_passage_or_identity_truth_created':False,'source_pixel_note':'Stored pixel hash refers to decoded BGR before JPEG compression. JPEG is a quality95 review derivative, not lossless source pixels.'}
    (OUT/'summary.json').write_text(json.dumps(output,indent=2));print(json.dumps({'status':output['status'],'cases':cases}),flush=True)


if __name__=='__main__':main()
