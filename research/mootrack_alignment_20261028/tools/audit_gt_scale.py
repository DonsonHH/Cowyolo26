"""Diagnostic scale control motivated by the pinned author's img_resize=0.5."""
from pathlib import Path
import hashlib,json,zipfile
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=ROOT/'results/scale_control';out.mkdir(parents=True,exist_ok=False)
    review=ROOT/'results/frame_review';frames=json.loads((review/'summary.json').read_text(encoding='utf-8'))['frames']
    archive=ROOT.parent/'counting_reference_candidates_20261027/catalog/MooTrack360_TrackEval_evaluation_code.zip'
    assert sha(archive)=='26800ea3b6e653e4e9d7c54a2587060bd2a920b4e862f0b84afef624234b6478'
    with zipfile.ZipFile(archive) as z:
        names=[n for n in z.namelist() if n.endswith(('.xml','.ini')) or 'seqmap' in n.lower()]
        body=z.read('TrackEval_evaluation_code/TrackEval/data/gt/mot_challenge/1hour/gt/gt.txt')
    rows=0;native_bad=0;half_bad=0;extrema=[1e12,1e12,-1,-1];tail=[]
    for line in body.decode().splitlines():
        v=line.split(',');x,y,w,h=map(float,v[2:6]);rows+=1
        half_bad+=int(x<0 or y<0 or x+w>1472 or y+h>1472)
        native_bad+=int(2*x<0 or 2*y<0 or 2*(x+w)>2944 or 2*(y+h)>2944)
        extrema=[min(extrema[0],x),min(extrema[1],y),max(extrema[2],x+w),max(extrema[3],y+h)]
        if int(v[0])==53920:tail.append(v[:6])
    tiles=[];native_scaled_files=[]
    for f in frames:
        original=f['video_display_frame0'];src=review/f['native_png'];assert sha(src)==f['native_sha256']
        image=Image.open(src).convert('RGB');overlay=image.copy();draw=ImageDraw.Draw(overlay)
        for box in f['GT_boxes']:
            x,y,w,h=[2*v for v in box['xywh']]
            draw.rectangle([x,y,x+w,y+h],outline='#22e8d1',width=7)
            draw.text((x+8,y+8),f"GT {box['track_ID']}",font=font(36),fill='white',stroke_width=2,stroke_fill='black')
        draw.rectangle([0,0,2944,108],fill='black')
        draw.text((25,15),'ADDED LAYER: GT x2, following author img_resize=0.5',font=font(33),fill='white')
        draw.text((25,57),f"frame hypothesis: video0 {original} -> GT1 {original+1}; not full-sequence certification",font=font(30),fill='#fbbf24')
        target=out/f'target_{original:05d}_GT_x2.png';overlay.save(target)
        native_scaled_files.append({'video_frame0':original,'GT_frame1_hypothesis':original+1,'path':target.name,'sha256':sha(target)})
        row=Image.new('RGB',(1800,1000),'#111827');d=ImageDraw.Draw(row)
        d.text((20,15),f"Video frame0 {original} | Native pixels (left) | GT x2 diagnostic (right)",font=font(29),fill='white')
        d.text((20,55),'Scale suggested by author configuration; no model predictions; alignment is still provisional.',font=font(24),fill='#fbbf24')
        row.paste(image.resize((880,880)),(10,110));row.paste(overlay.resize((880,880)),(910,110));tiles.append(row)
    contact=Image.new('RGB',(1800,1000*len(tiles)))
    for i,t in enumerate(tiles):contact.paste(t,(0,1000*i))
    contact.save(out/'native_and_GT_x2_diagnostic.jpg',quality=94)
    result={'status':'AUTHOR_CONFIG_MOTIVATED_SPATIAL_SCALE_CONTROL_READY_FOR_VISUAL_REVIEW','diagnostic_not_preregistered':True,
            'reason':'Direct raw-coordinate overlays mismatched; pinned README independently specifies img_resize=0.5.',
            'scale':2.0,'translation':[0,0],'GT_rows_checked':rows,'GT_xyxy_extrema_raw':extrema,'raw_boxes_outside_1472_square':half_bad,
            'scaled_boxes_outside_2944_square':native_bad,'archive_xml_ini_seqmap_members':names,
            'last_GT_frame_rows':tail,'images':native_scaled_files,'full_frame_alignment_certified':False,
            'three_samples_not_independent_holdout':True,'native_video_burned_boxes_assessment':'PENDING_VISUAL_REVIEW',
            'new_accuracy_claim':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['archive_xml_ini_seqmap_members','last_GT_frame_rows','images']}))

if __name__=='__main__':main()
