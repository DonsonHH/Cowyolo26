"""Disambiguate which visible cow each representative panel refers to; no measured centres."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
draft=json.loads((ROOT/'reference/assistant_event_draft_v1.json').read_text(encoding='utf-8'))
points={'R01':[800,1250],'R02':[500,1250],'R03':[850,1120],'R04':[500,1200],
        'R05':[840,1100],'R06':[780,1070],'R07':[770,1360],'R08':[780,1150],
        'R09':[820,1120],'R10':[420,1270],'R11':[420,1190],'R12':[500,1150]}
out=ROOT/'results/review_bundle';sheet=Image.new('RGB',(1600,1760),'#111827');d=ImageDraw.Draw(sheet)
d.text((15,7),'NEW CLIP: 12 assistant candidates; pending review, separate from user-confirmed12',font=font(26),fill='white')
d.text((15,44),'Magenta ring identifies the candidate in each panel; manual aid, NOT measured centre or model output.',font=font(22),fill='#fbbf24')
for i,r in enumerate(draft['candidates']):
    witness=r['source_witnesses'][4];src=ROOT/witness['source_image'];assert sha(src)==witness['source_sha256']
    with Image.open(src) as im:image=im.convert('RGB').resize((350,480))
    draw=ImageDraw.Draw(image);x,y=[v/3 for v in points[r['reference_ID']]]
    draw.ellipse([x-14,y-14,x+14,y+14],outline='#ff40bc',width=4)
    draw.text((max(2,min(250,x-70)),max(2,y-44)),r['reference_ID'],font=font(23),fill='#ff40bc',stroke_width=1,stroke_fill='black')
    panel=Image.new('RGB',(400,550),'#111827');draw=ImageDraw.Draw(panel)
    draw.text((12,5),r['reference_ID']+' | Downward candidate',font=font(21),fill='white')
    draw.text((12,35),f"Source f{witness['frame0']} | manual marker",font=font(19),fill='#fbbf24');panel.paste(image,(25,70))
    sheet.paste(panel,((i%4)*400,100+(i//4)*550))
dest=out/'twelve_draft_candidates_marked_overview_v2.jpg';assert not dest.exists();sheet.save(dest,quality=95)
guide=ROOT/'逐事件草案复核入口.md';before=guide.read_bytes();backup=out/'guide_before_target_markers.md';assert not backup.exists();backup.write_bytes(before)
text=before.decode('utf-8');old=(out/'twelve_draft_candidates_native_overview.jpg').as_posix();assert old in text
text=text.replace(old,dest.as_posix()).replace('图中为未经检测器绘框的原生像素，参考ID只供本次复核，不是注册牛只身份。',
    '图中为未经检测器绘框的原生像素，洋红色圆圈只帮助指出本格要看的牛，不是测量中心或模型输出；原始无标记图另外保留。参考ID只供本次复核，不是注册牛只身份。')
guide.write_text(text,encoding='utf-8')
record={'status':'MANUAL_TARGET_MARKERS_ADDED_TO_DISAMBIGUATE_DENSE_PANELS','overview_path':str(dest),'overview_sha256':sha(dest),
        'manual_marker_points_native_crop_xy':points,'points_are_not_measured_torso_centres':True,'raw_source_images_unchanged':True,
        'unmarked_overview_retained':True,'pre_marker_guide_sha256':sha(backup),'current_guide_sha256':sha(guide),
        'candidate_count_or_event_rules_changed':False,'eligible_for_final_scoring':False}
(out/'marked_overview_v2.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record),flush=True)
