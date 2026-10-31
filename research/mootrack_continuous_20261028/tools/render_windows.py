"""Render frozen continuous native/GT audit windows without running a detector."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def exact_read(pipe,n):
    b=bytearray()
    while len(b)<n:
        block=pipe.read(n-len(b))
        if not block:break
        b.extend(block)
    return bytes(b)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--window',required=True);a=parser.parse_args()
    protocol_path=ROOT/'protocol/continuous_births_v1.json';p=json.loads(protocol_path.read_text(encoding='utf-8'))
    expected=next(w for w in p['windows'] if w['name']==a.window)
    folder=ROOT/'evidence/video_ranges';complete=json.loads((folder/(a.window+'.complete.json')).read_text(encoding='utf-8'))
    for k,v in expected.items():assert complete[k]==v
    src=folder/complete['elementary_file'];assert sha(src)==complete['elementary_sha256']
    out=ROOT/'results'/a.window;out.mkdir(parents=True,exist_ok=False)
    archive=PROJECT/'counting_reference_candidates_20261027/catalog/MooTrack360_TrackEval_evaluation_code.zip';assert sha(archive)==p['GT_zip_sha256']
    with zipfile.ZipFile(archive) as z:body=z.read('TrackEval_evaluation_code/TrackEval/data/gt/mot_challenge/1hour/gt/gt.txt')
    assert hashlib.sha256(body).hexdigest()==p['GT_member_sha256'];gt={}
    for line in body.decode().splitlines():
        v=line.split(',');frame=int(v[0]);video=frame-1
        if expected['review_start_video0']<=video<expected['review_end_video0_exclusive']:
            gt.setdefault(video,[]).append({'ID':int(v[1]),'xywh':[float(x)*2 for x in v[2:6]]})
    probe_cmd=['ffprobe','-v','error','-count_frames','-show_entries','stream=width,height,nb_read_frames,codec_name','-of','json',str(src)]
    proc=subprocess.run(probe_cmd,capture_output=True,check=True);(out/'ffprobe.json').write_bytes(proc.stdout);(out/'ffprobe.stderr.log').write_bytes(proc.stderr)
    probe=json.loads(proc.stdout);stream=probe['streams'][0]
    assert (stream['width'],stream['height'])==(2944,2944) and int(stream['nb_read_frames'])==expected['decode_frames']
    movie=out/'native_and_publisher_GT.mp4';crop_movie=out/'gate_native_and_GT.mp4'
    def encoder(dest,dimensions,log):
        cmd=['ffmpeg','-hide_banner','-v','warning','-f','rawvideo','-pix_fmt','rgb24','-s',dimensions,'-r','30000/2002','-i','pipe:0',
             '-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(dest)]
        return subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log),cmd
    anchors=[];gtrows=[];sheet_panels=[];crop_panels=[]
    with (out/'decode.log').open('wb') as dec_log,(out/'encode.log').open('wb') as enc_log,(out/'encode_gate.log').open('wb') as gate_log:
        decoder_cmd=['ffmpeg','-hide_banner','-v','warning','-threads','2','-i',str(src),'-an','-fps_mode','passthrough','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
        decoder=subprocess.Popen(decoder_cmd,stdout=subprocess.PIPE,stderr=dec_log)
        enc,enc_cmd=encoder(movie,'1472x816',enc_log);gate_enc,gate_cmd=encoder(crop_movie,'1200x620',gate_log)
        try:
            count=0;rendered=0
            while True:
                raw=exact_read(decoder.stdout,2944*2944*3)
                if not raw:break
                assert len(raw)==2944*2944*3
                video=expected['decode_start_video0']+count;count+=1
                if not expected['review_start_video0']<=video<expected['review_end_video0_exclusive']:continue
                native=Image.frombytes('RGB',(2944,2944),raw);small=native.resize((736,736),Image.Resampling.LANCZOS)
                right=small.copy();d=ImageDraw.Draw(right)
                for box in gt.get(video,[]):
                    x,y,w,h=[v/4 for v in box['xywh']];color='#ffb347' if box['ID']==expected['publisher_ID'] else '#2de3d1'
                    d.rectangle([x,y,x+w,y+h],outline=color,width=2);d.text((x+2,y+2),f"GT {box['ID']}",fill=color,font=font(16),stroke_width=1,stroke_fill='black')
                canvas=Image.new('RGB',(1472,816),'#111827');c=ImageDraw.Draw(canvas)
                c.text((14,5),f"Publisher ID {expected['publisher_ID']} first-GT window | video0 {video} | {(video-expected['center_video_frame0_hypothesis'])*2002/30000:+.3f}s",font=font(23),fill='white')
                c.text((14,37),'Native source (left) | ADDED publisher GT x2, frame mapping provisional (right)',font=font(22),fill='#fbbf24')
                canvas.paste(small,(0,80));canvas.paste(right,(736,80));enc.stdin.write(canvas.tobytes())
                crop=native.crop((600,1700,1600,2600));crop_right=crop.copy();c=ImageDraw.Draw(crop_right)
                for box in gt.get(video,[]):
                    x,y,w,h=box['xywh'];x-=600;y-=1700;color='#ffb347' if box['ID']==expected['publisher_ID'] else '#2de3d1'
                    if x+w<0 or y+h<0 or x>1000 or y>900:continue
                    c.rectangle([x,y,x+w,y+h],outline=color,width=5);c.text((max(0,x+5),max(0,y+5)),f"GT {box['ID']}",font=font(32),fill=color,stroke_width=2,stroke_fill='black')
                gate=Image.new('RGB',(1200,620),'#111827');c=ImageDraw.Draw(gate)
                c.text((12,5),f"Fixed gate crop | Publisher ID {expected['publisher_ID']} | video0 {video} | GT1 {video+1}",font=font(24),fill='white')
                c.text((12,37),'Native crop (left) | Added GT hypothesis (right); first GT is not a passage event',font=font(21),fill='#fbbf24')
                gate.paste(crop.resize((600,540)),(0,80));gate.paste(crop_right.resize((600,540)),(600,80));gate_enc.stdin.write(gate.tobytes())
                gtrows.append({'video_frame0':video,'GT_frame1':video+1,'publisher_target_present':any(b['ID']==expected['publisher_ID'] for b in gt.get(video,[])),
                               'publisher_boxes_native_scale':gt.get(video,[])})
                if video in expected['native_anchor_frames0']:
                    path=out/f'video0_{video:05d}_native.png';native.save(path)
                    anchors.append({'video_frame0':video,'GT_frame1':video+1,'path':path.name,'sha256':sha(path)})
                    panel=canvas.copy();panel.thumbnail((1472,816));sheet_panels.append((video,panel));crop_panels.append((video,gate.copy()))
                rendered+=1
            assert count==expected['decode_frames'] and rendered==90 and len(anchors)==5
            assert decoder.wait()==0
            enc.stdin.close();gate_enc.stdin.close();assert enc.wait()==gate_enc.wait()==0
        except BaseException:
            for proc in [decoder,enc,gate_enc]:
                if proc.poll() is None:proc.terminate();proc.wait()
            raise
    for label,panels,dimensions in [('full',sheet_panels,(1472,816)),('gate',crop_panels,(1200,620))]:
        panels.sort();sheet=Image.new('RGB',(dimensions[0],dimensions[1]*len(panels)))
        for i,(_,im) in enumerate(panels):sheet.paste(im,(0,dimensions[1]*i))
        sheet.save(out/(label+'_five_anchors.jpg'),quality=94)
    (out/'publisher_GT_rows.json').write_text(json.dumps(gtrows,indent=2),encoding='utf-8')
    result={'status':'CONTINUOUS_NATIVE_GT_AND_FIXED_GATE_CROP_RENDERED','name':a.window,'publisher_ID':expected['publisher_ID'],
            'protocol_sha256':sha(protocol_path),'source_elementary_sha256':sha(src),'decode_frames':count,'render_frames':rendered,
            'review_source_frames0':[expected['review_start_video0'],expected['review_end_video0_exclusive']-1],
            'native_anchors':anchors,'videos':[{'file':v.name,'sha256':sha(v),'bytes':v.stat().st_size} for v in [movie,crop_movie]],
            'decode_command':decoder_cmd,'encode_command':enc_cmd,'gate_encode_command':gate_cmd,
            'duration_expected_s':90*2002/30000,'all_GT_source_rows':sum(len(r['publisher_boxes_native_scale']) for r in gtrows),
            'new_detector_inference':False,'full_GT_alignment_certified':False,'complete_passages_certified':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ['status','name','decode_frames','render_frames','all_GT_source_rows']}),flush=True)

if __name__=='__main__':main()
