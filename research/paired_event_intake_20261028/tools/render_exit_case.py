from pathlib import Path
import hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
FRAMES=[9355,9360,9365,9370,9375,9380]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dashed(draw,box,color):
    x0,y0,x1,y1=box
    for x in range(round(x0),round(x1),14):
        draw.line((x,y0,min(x+8,x1),y0),fill=color,width=3);draw.line((x,y1,min(x+8,x1),y1),fill=color,width=3)
    for y in range(round(y0),round(y1),14):
        draw.line((x0,y,x0,min(y+8,y1)),fill=color,width=3);draw.line((x1,y,x1,min(y+8,y1)),fill=color,width=3)
def main():
    out=ROOT/'figures';assert not out.exists();out.mkdir()
    trace=load(ROOT/'exit_probe_delivery/results/exit_probe/association_trace.json');byframe={t['source_frame']:t for t in trace}
    source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4'
    protocol=load(ROOT/'protocol/evaluation_v1.json');assert sha(source)==load(ROOT/'results/frozen_prediction_catalog_v2.json')['source_sha256']
    select='+'.join(f'eq(n\\,{f})' for f in FRAMES)
    run=subprocess.run([shutil.which('ffmpeg'),'-hide_banner','-nostdin','-n','-i',str(source),'-vf','select='+select,
                        '-fps_mode','vfr','-frames:v',str(len(FRAMES)),'-q:v','2',str(out/'native_%02d.jpg')],capture_output=True)
    (ROOT/'results/exit_case_decode.log').write_bytes(run.stderr);assert run.returncode==0,run.stderr[-1000:]
    paths=sorted(out.glob('native_*.jpg'));assert len(paths)==6
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    raw=Image.new('RGB',(1920,788),'white');annotated=Image.new('RGB',raw.size,'white');rd=ImageDraw.Draw(raw);ad=ImageDraw.Draw(annotated)
    for j,(frame,path) in enumerate(zip(FRAMES,paths)):
        with Image.open(path) as image:image.load();assert image.size==(2560,1440);picture=image.resize((640,360))
        x=(j%3)*640;y=(j//3)*394;raw.paste(picture,(x,y));rd.text((x+8,y+364),f'Source{frame} | {frame/25:.2f}s | no predictions',font=font,fill='black')
        picture=picture.copy();draw=ImageDraw.Draw(picture);t=byframe[frame]
        for gx in [.34,.75]:draw.line((gx*640,0,gx*640,360),fill='#efae31',width=2)
        for gy in [.4,.6]:draw.line((.34*640,gy*360,.75*640,gy*360),fill='#efae31',width=2)
        for i,box in enumerate(t['raw_boxes']):
            x0,y0,x1,y1,score,_=box
            if not .34<(x0+x1)/5120<.75:continue
            rect=tuple(v/4 for v in [x0,y0,x1,y1]);color='#00bdd5' if score>=.25 else '#f3e055'
            draw.rectangle(rect,outline=color,width=2);draw.text((rect[0],max(0,rect[1]-17)),f'raw{i} {score:.3f}',font=font,fill=color,stroke_width=1,stroke_fill='black')
        target=t['target_after'];rect=tuple(v/4 for v in target['xyxy'])
        if t['target_output_in_ROI']:draw.rectangle(rect,outline='#ed5286',width=3)
        else:dashed(draw,rect,'#ed5286')
        draw.text((max(0,rect[0]),max(0,rect[1]-34)),'ID117 '+('output' if t['target_output_in_ROI'] else 'lost prediction'),font=font,fill='#ed5286',stroke_width=1,stroke_fill='black')
        annotated.paste(picture,(x,y));ad.text((x+8,y+364),f'Source{frame} | ID117 '+('B output' if t['target_output_in_ROI'] else 'no tracked output'),font=font,fill='black')
    rawfile=out/'B_case_native_frames.jpg';figure=out/'B_case_raw_and_tracker.jpg';raw.save(rawfile,quality=93);annotated.save(figure,quality=93)
    record={'source_sha256':sha(source),'frames':FRAMES,'selection':'posthoc algorithm transition sequence of existing ID117 B interruption',
      'source_files':[{'frame':f,'path':p.name,'sha256':sha(p)} for f,p in zip(FRAMES,paths)],
      'figures':[{'path':p.name,'sha256':sha(p)} for p in [rawfile,figure]],
      'legend':{'cyan':'raw confidence>=0.25','yellow':'raw confidence<0.25','pink_solid':'ID117 actual tracked output','pink_dashed':'ID117 lost state prediction, not observation'},
      'raw_index_labels_reference_original_frame_rows':True,'new_inference':False,'independent_ground_truth':False,
      'visual_QA':'PENDING'}
    p=ROOT/'results/exit_case_figure_record.json';assert not p.exists();p.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'frames':6,'contact_sheets':2,'visual_QA':'PENDING'}))
if __name__=='__main__':main()
