"""Decode three predeclared native frames; draw publisher GT as a labelled hypothesis."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(size):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',size)

def main():
    out=ROOT/'results/frame_review';out.mkdir(parents=True,exist_ok=False)
    ranges=ROOT/'evidence/video_ranges';meta=json.loads((ranges/'manifest.json').read_text(encoding='utf-8'))
    archive=ROOT.parent/'counting_reference_candidates_20261027/catalog/MooTrack360_TrackEval_evaluation_code.zip'
    assert sha(archive)=='26800ea3b6e653e4e9d7c54a2587060bd2a920b4e862f0b84afef624234b6478'
    wanted={g['target_display_index0']+1 for g in meta['GOPs']};gt={i:[] for i in wanted}
    with zipfile.ZipFile(archive) as z:
        body=z.read('TrackEval_evaluation_code/TrackEval/data/gt/mot_challenge/1hour/gt/gt.txt')
    assert hashlib.sha256(body).hexdigest()=='595cdad9581382da5f3f406b2259f3d6937b1a131f6d677eca5756bdfcabccbd'
    for line in body.decode().splitlines():
        row=line.split(',');frame=int(row[0])
        if frame in wanted:gt[frame].append({'track_ID':int(row[1]),'xywh':[float(v) for v in row[2:6]]})
    result=[];tiles=[]
    for g in meta['GOPs']:
        original=g['target_display_index0'];tag=f'target_{original:05d}';src=ranges/g['elementary_file']
        assert sha(src)==g['elementary_sha256']
        cmd=['ffprobe','-v','error','-count_frames','-show_entries','stream=width,height,nb_read_frames,codec_name','-of','json',str(src)]
        proc=subprocess.run(cmd,capture_output=True,check=True);probe=json.loads(proc.stdout)
        probe_stderr=proc.stderr.decode(errors='replace')
        (out/(tag+'_ffprobe.json')).write_bytes(proc.stdout)
        assert len(probe['streams'])==1;stream=probe['streams'][0]
        assert (stream['width'],stream['height'])==(2944,2944)
        assert int(stream['nb_read_frames'])==g['end_decode_index0_exclusive']-g['start_decode_index0']==30
        dest=out/(tag+'_native.png')
        cmd=['ffmpeg','-hide_banner','-v','warning','-threads','2','-i',str(src),'-vf',f"select=eq(n\\,{g['target_local_frame0']})",'-frames:v','1','-fps_mode','vfr',str(dest)]
        proc=subprocess.run(cmd,capture_output=True,check=True)
        (out/(tag+'_decode.log')).write_bytes(proc.stderr)
        image=Image.open(dest).convert('RGB');assert image.size==(2944,2944)
        native=image.copy();overlay=image.copy();draw=ImageDraw.Draw(overlay)
        for box in gt[original+1]:
            x,y,w,h=box['xywh'];draw.rectangle([x,y,x+w,y+h],outline='#ff3dc8',width=7)
            draw.text((x+7,y+7),f"GT {box['track_ID']}",fill='white',stroke_width=2,stroke_fill='black',font=font(32))
        draw.rectangle([0,0,2944,95],fill='black')
        draw.text((25,20),f'ADDED GT HYPOTHESIS: video frame0 {original} <-> GT frame1 {original+1}',font=font(35),fill='white')
        added=out/(tag+'_GT_hypothesis.png');overlay.save(added)
        native.save(out/(tag+'_native.jpg'),quality=94)
        seconds=original*2002/30000
        row=Image.new('RGB',(1800,980),'#111827');d=ImageDraw.Draw(row)
        d.text((20,15),f'Video frame0 {original} | {seconds:.3f}s | Native pixels (left), added GT hypothesis (right)',font=font(27),fill='white')
        d.text((20,55),'Hypothesis is an inspection aid; whole-video alignment is NOT certified.',font=font(24),fill='#fbbf24')
        row.paste(native.resize((880,880)),(10,95));row.paste(overlay.resize((880,880)),(910,95));tiles.append(row)
        result.append({'video_display_frame0':original,'video_time_seconds':seconds,'GT_frame1_hypothesis':original+1,
                       'GT_boxes':gt[original+1],'decoded_frames':30,'native_png':dest.name,'native_sha256':sha(dest),
                       'GT_overlay':added.name,'GT_overlay_sha256':sha(added),'contains_overlay_assessment':'PENDING_VISUAL_REVIEW',
                       'decode_command':cmd,'ffprobe':probe,'ffprobe_stderr':probe_stderr,
                       'ffmpeg_stderr':proc.stderr.decode(errors='replace')})
    contact=Image.new('RGB',(1800,980*len(tiles)))
    for n,tile in enumerate(tiles):contact.paste(tile,(0,980*n))
    contact.save(out/'three_times_native_and_GT_hypothesis.jpg',quality=94)
    summary={'status':'THREE_NATIVE_FRAMES_AND_LABELLED_GT_HYPOTHESES_DECODED','frames':result,
             'total_native_video_frames_decoded_for_integrity_check':90,'ffmpeg_version':subprocess.run(['ffmpeg','-version'],capture_output=True,check=True).stdout.decode().splitlines()[0],
             'all_frame_alignment_certified':False,'new_inference_or_training':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({'status':summary['status'],'dimensions':[2944,2944],'original_display_indices0':[g['target_display_index0'] for g in meta['GOPs']],
                      'GT_box_counts_hypothesis':[len(gt[g['target_display_index0']+1]) for g in meta['GOPs']]}),flush=True)

if __name__=='__main__':main()
