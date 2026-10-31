"""Inspect the annotated endpoint and final source frame without extending labels."""
from pathlib import Path
import hashlib,json,subprocess
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)

def main():
    out=ROOT/'results/tail_review';out.mkdir(parents=True,exist_ok=False)
    meta=json.loads((ROOT/'evidence/tail_ranges/manifest.json').read_text(encoding='utf-8'))
    last=json.loads((ROOT/'results/scale_control/summary.json').read_text(encoding='utf-8'))['last_GT_frame_rows']
    rows=[];tiles=[]
    for g in meta['GOPs']:
        native_frame=g['target_display_index0'];tag=f'target_{native_frame:05d}'
        src=ROOT/'evidence/tail_ranges'/g['elementary_file'];assert sha(src)==g['elementary_sha256']
        command=['ffprobe','-v','error','-count_frames','-show_entries','stream=width,height,nb_read_frames,codec_name','-of','json',str(src)]
        p=subprocess.run(command,capture_output=True,check=True);probe=json.loads(p.stdout)
        (out/(tag+'_ffprobe.json')).write_bytes(p.stdout)
        (out/(tag+'_ffprobe.stderr.log')).write_bytes(p.stderr)
        stream=probe['streams'][0];assert (stream['width'],stream['height'])==(2944,2944)
        assert int(stream['nb_read_frames'])==g['end_decode_index0_exclusive']-g['start_decode_index0']
        dest=out/(tag+'_native.png')
        cmd=['ffmpeg','-hide_banner','-v','warning','-threads','2','-i',str(src),'-vf',f"select=eq(n\\,{g['target_local_frame0']})",'-frames:v','1','-fps_mode','vfr','-update','1',str(dest)]
        p=subprocess.run(cmd,capture_output=True,check=True);(out/(tag+'_decode.log')).write_bytes(p.stderr)
        image=Image.open(dest).convert('RGB');assert image.size==(2944,2944)
        image.save(out/(tag+'_native.jpg'),quality=94);overlay=image.copy();draw=ImageDraw.Draw(overlay)
        for v in last:
            x,y,w,h=[float(x)*2 for x in v[2:6]]
            draw.rectangle([x,y,x+w,y+h],outline='#22e8d1',width=7)
            draw.text((x+8,y+8),f'LAST GT {v[1]}',font=font(36),fill='white',stroke_width=2,stroke_fill='black')
        note='Endpoint mapping hypothesis' if native_frame==53919 else 'CONTEXT ONLY: NO GT EXISTS FOR THIS VIDEO FRAME'
        draw.rectangle([0,0,2944,115],fill='black')
        draw.text((25,15),f'ADDED: LAST GT FRAME 53920 x2 ON VIDEO frame0 {native_frame}',font=font(32),fill='white')
        draw.text((25,60),note,font=font(31),fill='#fbbf24')
        added=out/(tag+'_last_GT_context.png');overlay.save(added)
        row=Image.new('RGB',(1800,1000),'#111827');d=ImageDraw.Draw(row)
        d.text((20,15),f'Video frame0 {native_frame} ({native_frame*2002/30000:.3f}s) | Native (left), last GT x2 (right)',font=font(27),fill='white')
        d.text((20,55),note,font=font(25),fill='#fbbf24')
        row.paste(image.resize((880,880)),(10,110));row.paste(overlay.resize((880,880)),(910,110));tiles.append(row)
        rows.append({'video_frame0':native_frame,'video_time_s':native_frame*2002/30000,
                     'GT_frame1_hypothesis':53920 if native_frame==53919 else None,'last_GT_context_only':native_frame!=53919,
                     'native':dest.name,'native_sha256':sha(dest),'overlay':added.name,'overlay_sha256':sha(added),
                     'decoded_frames':int(stream['nb_read_frames']),'decode_command':cmd,
                     'visual_assessment':'PENDING_VISUAL_REVIEW'})
    contact=Image.new('RGB',(1800,1000*len(tiles)))
    for i,t in enumerate(tiles):contact.paste(t,(0,1000*i))
    contact.save(out/'endpoint_and_final_native_GT_context.jpg',quality=94)
    result={'status':'ANNOTATED_ENDPOINT_AND_FINAL_SOURCE_FRAME_DECODED','frames':rows,'GT_last_frame1':53920,
            'source_last_frame0':53945,'extra_video_frames_after_GT_prefix_hypothesis':26,'extra_duration_seconds':26*2002/30000,
            'tail_truncation_is_proven':False,'no_GT_rows_fabricated_or_extrapolated':True,
            'GOP_frames_decoded':sum(r['decoded_frames'] for r in rows),'full_GT_alignment_certified':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)

if __name__=='__main__':main()
