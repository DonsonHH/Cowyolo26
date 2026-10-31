from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    cases=load(ROOT/'results/ROI_recovery_case_states.json')['cases'];frames=sorted({f for c in cases for f in [c['last_observed_frame'],c['recovery_source_frame'],c['recovery_source_frame']+5]})
    folder=ROOT/'case_figures';assert not folder.exists();folder.mkdir()
    source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';assert sha(source)==load(ROOT/'protocol/lost_v1.json')['source_sha256']
    select='+'.join(f'eq(n\\,{f})' for f in frames)
    run=subprocess.run([shutil.which('ffmpeg'),'-hide_banner','-nostdin','-n','-i',str(source),'-vf','select='+select,'-fps_mode','vfr',
                        '-frames:v',str(len(frames)),'-q:v','2',str(folder/'native_%02d.jpg')],capture_output=True)
    (ROOT/'results/case_decode.log').write_bytes(run.stderr);assert run.returncode==0,run.stderr[-1000:]
    images=sorted(folder.glob('native_*.jpg'));assert len(images)==len(frames);image_index=dict(zip(frames,images))
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);figures=[]
    sheet=Image.new('RGB',(1920,4*388),'white');sheetdraw=ImageDraw.Draw(sheet)
    for j,c in enumerate(cases):
        seed,tid=c['seed'],c['target_ID'];index=defaultdict(list)
        with (ROOT/f'delivery/results/allow_lost_iou_seed{seed}/source_tracks.csv').open(encoding='utf-8',newline='') as f:
            for row in csv.DictReader(f):index[int(row['source_frame'])].append(row)
        for k,frame in enumerate([c['last_observed_frame'],c['recovery_source_frame'],c['recovery_source_frame']+5]):
            with Image.open(image_index[frame]) as image:image.load();assert image.size==(2560,1440);p=image.resize((640,360))
            draw=ImageDraw.Draw(p)
            for x in [.34,.75]:draw.line((640*x,0,640*x,360),fill='#edae2e',width=2)
            for y in [.4,.6]:draw.line((640*.34,360*y,640*.75,360*y),fill='#edae2e',width=2)
            for r in index[frame]:
                rect=tuple(float(r[f])/4 for f in ['x1','y1','x2','y2']);focus=int(r['track_id'])==tid;color='#ee5987' if focus else '#9be3b4'
                draw.rectangle(rect,outline=color,width=3 if focus else 1);draw.text((rect[0],max(0,rect[1]-19)),f'ID{r["track_id"]} {float(r["confidence"]):.2f}',font=font,fill=color,stroke_width=1,stroke_fill='black')
            sheet.paste(p,(k*640,j*388));label=['Last observation','Low-score recovery','Next sampled frame'][k]
            sheetdraw.text((k*640+8,j*388+363),f'seed{seed} ID{tid} | source{frame} | {label}',font=font,fill='black')
    target=folder/'four_ROI_recoveries.jpg';sheet.save(target,quality=93);figures.append(target)
    record={'source_sha256':sha(source),'selection':'Allfouractual lowLost recoveries whose raw detection centers inROI and scope; no subset selection',
       'source_frames':frames,'source_images':[{'frame':f,'file':p.name,'sha256':sha(p)} for f,p in zip(frames,images)],
       'figures':[{'file':p.name,'sha256':sha(p)} for p in figures],
       'pink':'selected ID observed boxes, not predicted boxes','green':'other actual tracker outputs',
       'new_inference':False,'independent_ground_truth':False,'visual_QA':'PENDING'}
    path=ROOT/'results/case_figure_record.json';assert not path.exists();path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({'native_source_frames':len(frames),'all_ROI_cases':4,'visual_QA':'PENDING'}))
if __name__=='__main__':main()
