"""Render paired predictions on hash-checked native 5Hz source crops."""
from pathlib import Path
from collections import defaultdict
from PIL import Image,ImageDraw,ImageFont
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    source_root=PROJECT/'overhead_positive_reference_20261028/focused_delivery'
    source=load(source_root/'results/focused/summary.json')
    results=ROOT/'control_delivery/results/firststage_control'
    out=ROOT/'results/paired_previews';out.mkdir(exist_ok=False)
    modes=['original_fused','firststage_pure_IoU'];data={}
    for mode in modes:
        rows=load(results/mode/'post_tracker_boxes.json');by_frame=defaultdict(list)
        for row in rows:by_frame[row['frame0']].append(row)
        data[mode]={'boxes':by_frame,'events':load(results/mode/'handoff_events.json')}
    try:
        font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',20)
        small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',17)
        label=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',28)
    except OSError:font=small=label=ImageFont.load_default()
    cases={2645,2655,2665,2670,2675,3840};contacts=[];media=[];source_records=[]
    for window in source['windows']:
        name=window['name'];samples=window['samples'];start=samples[0]['frame0'];end=samples[-1]['frame0']+5
        video=out/(name+'_paired.mp4');log=out/(name+'_encode.log')
        with log.open('wb') as stderr:
            cmd=['ffmpeg','-hide_banner','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1080x840','-r','5','-i','pipe:0',
                 '-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(video)]
            proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=stderr)
            try:
                for index,row in enumerate(samples):
                    frame=row['frame0'];path=source_root/row['file'];assert sha(path)==row['sha256']
                    source_records.append({'frame0':frame,'path':str(path.resolve()),'sha256':sha(path)})
                    with Image.open(path) as im:assert im.size==(1050,1440);native=im.convert('RGB')
                    canvas=Image.new('RGB',(1080,840),'#111827');draw=ImageDraw.Draw(canvas)
                    draw.text((12,6),f'Native source frame0 {frame} | {frame/25:.2f}s | {name}',font=small,fill='white')
                    per_mode=[]
                    for column,mode in enumerate(modes):
                        view=native.copy();d=ImageDraw.Draw(view)
                        for y in [576,864]:d.line((0,y,1049,y),fill='#fbbf24',width=4)
                        for b in data[mode]['boxes'][frame]:
                            tid=b['track_id']
                            if tid is None or not .34<(b['x1']+b['x2'])/5120<.75:continue
                            box=[b['x1']-870,b['y1'],b['x2']-870,b['y2']]
                            d.rectangle(box,outline='#86efac',width=4)
                            text=f"ID {tid} {b['confidence']:.2f}";tx=max(0,min(820,box[0]));ty=max(0,box[1]-32)
                            d.text((tx,ty),text,font=label,fill='#86efac',stroke_width=1,stroke_fill='#111827')
                        events=[e for e in data[mode]['events'] if start<=e['frame0']<=frame and e['frame0']<end]
                        down=sum(e['direction']=='A->B' for e in events);up=sum(e['direction']=='B->A' for e in events)
                        x=10+column*535
                        draw.text((x,30),'Original fused first stage' if column==0 else 'Control: first stage pure IoU',font=font,fill='#bbf7d0')
                        draw.text((x,55),f'Predicted window down {down}; up {up}',font=small,fill='white')
                        canvas.paste(view.resize((525,720),Image.Resampling.LANCZOS),(x,80))
                        per_mode.append({'mode':mode,'down_so_far':down,'up_so_far':up})
                    draw.text((10,805),'5Hz samples at original time; same source pixels; reference pending.',font=small,fill='white')
                    draw.text((10,823),'Track IDs are temporary and cannot be equated across variants.',font=small,fill='white')
                    proc.stdin.write(canvas.tobytes())
                    if frame in cases:
                        target=out/f'comparison_{frame:05d}.jpg';canvas.save(target,quality=94)
                        contacts.append({'frame0':frame,'path':str(target.resolve()),'sha256':sha(target),'panels':2,
                                         'source_sha256':row['sha256'],'window':name,'predictions':per_mode,'video_frame0':index})
                proc.stdin.close();assert proc.wait()==0
            except BaseException:
                if proc.poll() is None:proc.terminate();proc.wait()
                raise
        assert log.stat().st_size==0
        probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries',
                              'stream=codec_name,width,height,nb_read_frames,avg_frame_rate','-of','json',str(video)],capture_output=True,text=True)
        assert probe.returncode==0 and not probe.stderr
        stream=json.loads(probe.stdout)['streams'][0]
        assert stream['codec_name']=='h264' and stream['avg_frame_rate']=='5/1'
        assert [stream['width'],stream['height']]==[1080,840] and int(stream['nb_read_frames'])==len(samples)
        strict=subprocess.run(['ffmpeg','-hide_banner','-v','error','-xerror','-threads','2','-i',str(video),'-an','-f','null','-'],capture_output=True,text=True)
        assert strict.returncode==0 and not strict.stderr
        media.append({'window':name,'path':str(video.resolve()),'sha256':sha(video),'decoded_frames':len(samples),
                      'fps':5,'dimensions':[1080,840],'strict_decode':'PASS','nominal_original_duration_s':len(samples)/5})
    assert len(contacts)==6 and len(media)==3 and len(source_records)==625
    record={'status':'THREE_PAIRED_NATIVE_5HZ_VIDEOS_FULLY_DECODED_AND_SIX_CASE_SHEETS_CREATED',
            'media':media,'contacts':contacts,'source_records':source_records,'source_frames_hash_checked':625,
            'video_frames_fully_decoded':625,'actual_visual_review_required':True,'new_detector_forwards':0,'formal_scores_computed':False}
    target=ROOT/'results/paired_media_verification.json';assert not target.exists();target.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['source_records','contacts']}))
if __name__=='__main__':main()
