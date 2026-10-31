"""Posthoc development case: native source frames and unchanged cached output."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
FRAMES=[9300,9305,9310,9315,9320,9330,9345,9360,9375]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def read(p):return list(csv.DictReader(Path(p).open(newline='',encoding='utf-8')))
def main():
    dest=ROOT/'source_case';assert not dest.exists();dest.mkdir()
    source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4'
    assert sha(source)==load(ROOT/'protocol/clock_v1.json')['source_video_sha256']
    select='+'.join(f'eq(n\\,{frame})' for frame in FRAMES)
    command=[shutil.which('ffmpeg'),'-hide_banner','-nostdin','-n','-i',str(source),'-vf','select='+select,'-fps_mode','vfr','-frames:v',str(len(FRAMES)),'-q:v','2',str(dest/'source_%02d.jpg')]
    run=subprocess.run(command,capture_output=True);(ROOT/'results/source_case_decode.log').write_bytes(run.stderr);assert run.returncode==0
    paths=sorted(dest.glob('source_*.jpg'));assert len(paths)==len(FRAMES)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    rawsheet=Image.new('RGB',(1920,3*388),'white');draw=ImageDraw.Draw(rawsheet)
    for j,(frame,path) in enumerate(zip(FRAMES,paths)):
        with Image.open(path) as image:image.load();assert image.size==(2560,1440);rawsheet.paste(image.resize((640,360)),((j%3)*640,(j//3)*388))
        draw.text(((j%3)*640+8,(j//3)*388+362),f'Source {frame} | {frame/25:.2f}s | no predictions',font=font,fill='black')
    rawsheet.save(dest/'native_frames_contact.jpg',quality=93)
    cases=[(26,95),(27,57),(28,117)];selected=[9310,9315,9320,9345,9360,9375];all_rows=[];figures=[]
    for seed,tid in cases:
        name=f'full640_5hz_seed{seed}';folder=PROJECT/'counting_recovery_20261028/delivery/results/replay_v2'/name
        if not folder.exists():folder=PROJECT/'counting_recovery_20261028/delivery/results/full640_confirmation'/name
        tracks=read(folder/'source_tracks.csv');raw=read(folder/'pretracker_boxes.csv')
        sheet=Image.new('RGB',(1920,2*388),'white');d=ImageDraw.Draw(sheet)
        for j,frame in enumerate(selected):
            path=paths[FRAMES.index(frame)]
            with Image.open(path) as image:im=image.resize((640,360)).copy()
            p=ImageDraw.Draw(im)
            for x in [.34,.75]:p.line((x*640,0,x*640,360),fill='#f0a900',width=2)
            for y in [.4,.6]:p.line((.34*640,y*360,.75*640,y*360),fill='#f0a900',width=2)
            for row in raw:
                if int(row['frame'])==frame and .34<(float(row['x1'])+float(row['x2']))/5120<.75:
                    p.rectangle(tuple(float(row[k])/4 for k in ['x1','y1','x2','y2']),outline='#00c7eb',width=1)
            for row in tracks:
                if int(row['source_frame'])!=frame:continue
                box=tuple(float(row[k])/4 for k in ['x1','y1','x2','y2']);focus=int(row['track_id'])==tid
                color='#ef5487' if focus else '#95e2a0';p.rectangle(box,outline=color,width=3 if focus else 1)
                p.text((box[0],max(0,box[1]-19)),f'ID{row["track_id"]}',font=font,fill=color,stroke_width=1,stroke_fill='black')
            sheet.paste(im,((j%3)*640,(j//3)*388));d.text(((j%3)*640+8,(j//3)*388+362),f'seed{seed} | source{frame} | focusID{tid}',font=font,fill='black')
        target=dest/f'seed{seed}_focusID{tid}.jpg';sheet.save(target,quality=93);figures.append(target)
        for row in tracks:
            if int(row['track_id'])==tid:all_rows.append({'seed':seed,**row})
    with (ROOT/'results/stability_case_rows.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(all_rows)
    record={'selection':'posthoc: allthree full640seeds have an uncounted multiobservation track near source9310',
      'source_sha256':sha(source),'frames':FRAMES,'seeds_and_focus_IDs':cases,'raw_frames':[
          {'source_frame':f,'file':p.name,'sha256':sha(p)} for f,p in zip(FRAMES,paths)],
      'figures':[{'file':p.name,'sha256':sha(p)} for p in [dest/'native_frames_contact.jpg',*figures]],
      'colors':{'cyan':'raw detection','green':'other tracked output','pink':'selected uncounted ID','orange':'fixed ROI and gates'},
      'counter_or_detector_changed':False,'new_inference':False,'independent_ground_truth':False,'visual_QA':'PENDING'}
    path=ROOT/'results/stability_case_record.json';assert not path.exists();path.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'frames':len(paths),'case_rows':len(all_rows),'visual_QA':'PENDING'}))
if __name__=='__main__':main()
