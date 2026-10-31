"""Fully decode twelve movies, verify time/frame metadata and make aligned cases."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFont
import hashlib, json, subprocess

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

def verify(spec):
    model,row,window=spec;path=ROOT/'delivery'/row['path'];assert sha(path)==row['sha256']
    probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries',
                          'stream=width,height,r_frame_rate,avg_frame_rate,nb_read_frames,codec_name,duration','-of','json',str(path)],capture_output=True,text=True)
    assert probe.returncode==0 and not probe.stderr,probe.stderr
    stream=json.loads(probe.stdout)['streams'][0]
    assert (stream['width'],stream['height'])==(1280,720) and stream['codec_name']=='h264'
    assert stream['r_frame_rate']==stream['avg_frame_rate']=='25/1' and int(stream['nb_read_frames'])==row['frames']
    assert row['frames']==window['end_frame0_exclusive']-window['start_frame0']
    decoded=subprocess.run(['ffmpeg','-hide_banner','-v','error','-xerror','-threads','2','-i',str(path),'-an','-f','null','-'],capture_output=True,text=True)
    assert decoded.returncode==0 and not decoded.stderr,decoded.stderr
    return {'model':model,'window':row['window'],'path':str(path.resolve()),'sha256':sha(path),
            'frames':int(stream['nb_read_frames']),'fps':25,'dimensions':[1280,720],'strict_decode':'PASS'}

def main():
    p=load(ROOT/'protocol/replay_v1.json');jobs=[]
    for spec in p['models']:
        summary=load(ROOT/'delivery/results'/spec['name']/'summary.json')
        for row,window in zip(summary['media'],p['windows']):assert row['window']==window['name'];jobs.append((spec['name'],row,window))
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(verify,jobs))
    assert len(rows)==12 and sum(r['frames'] for r in rows)==12500
    folder=ROOT/'results/aligned_cases';folder.mkdir(exist_ok=False)
    cases=[2640,2720,2920,3380,3605,3825,4005,5320,9900]
    try:font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',22)
    except OSError:font=ImageFont.load_default()
    contacts=[]
    for frame in cases:
        window=next(w for w in p['windows'] if w['start_frame0']<=frame<w['end_frame0_exclusive'])
        canvas=Image.new('RGB',(1304,832),'#111827');draw=ImageDraw.Draw(canvas)
        draw.text((12,8),f'Same native source frame0 {frame} ({frame/25:.2f}s); predictions only',font=font,fill='white')
        panels=[]
        for index,spec in enumerate(p['models']):
            model=spec['name'];video=ROOT/'delivery/results'/model/window['name']/'predictions.mp4'
            image=folder/f'{frame:05d}_{model}.png'
            cmd=['ffmpeg','-hide_banner','-v','error','-xerror','-i',str(video),'-vf',f'select=eq(n\\,{frame-window["start_frame0"]})',
                 '-frames:v','1','-fps_mode','vfr',str(image)]
            result=subprocess.run(cmd,capture_output=True,text=True);assert result.returncode==0 and not result.stderr,result.stderr
            with Image.open(image) as im:
                assert im.size==(1280,720);panel=im.convert('RGB').resize((640,360),Image.Resampling.LANCZOS)
            x=12+(index%2)*652;y=44+(index//2)*394
            draw.text((x,y),model,font=font,fill='#bbf7d0');canvas.paste(panel,(x,y+28))
            panels.append({'model':model,'path':str(image.resolve()),'sha256':sha(image),'source_frame0':frame,
                           'video_sha256':sha(video),'video_frame0':frame-window['start_frame0']})
        target=folder/f'comparison_{frame:05d}.jpg';canvas.save(target,quality=94)
        contacts.append({'source_frame0':frame,'path':str(target.resolve()),'sha256':sha(target),'panels':panels})
    record={'status':'TWELVE_PREDICTION_MOVIES_FULLY_DECODED_AND_NINE_ALIGNED_CASE_SHEETS_CREATED',
            'media':rows,'movie_count':12,'decoded_frames':12500,'case_sheets':contacts,'case_panels':36,
            'actual_visual_inspection_required':True,'formal_accuracy_or_F1_computed':False,'whole_goal_complete':False}
    save(ROOT/'results/media_verification.json',record)
    print(json.dumps({k:v for k,v in record.items() if k not in ['media','case_sheets']}))
if __name__=='__main__':main()
