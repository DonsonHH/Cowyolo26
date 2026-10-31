"""Create a compact inspectable reference guide, with unaccepted fields left explicit."""
from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def main():
    src=ROOT/'reference/assistant_event_draft_v1.json';draft=json.loads(src.read_text(encoding='utf-8'))
    out=ROOT/'results/review_bundle';out.mkdir(exist_ok=False);panels=[]
    for r in draft['candidates']:
        source=ROOT/r['source_witnesses'][4]['source_image'];assert sha(source)==r['source_witnesses'][4]['source_sha256']
        with Image.open(source) as im:image=im.convert('RGB').resize((350,480))
        panel=Image.new('RGB',(400,550),'#111827');d=ImageDraw.Draw(panel)
        d.text((12,8),r['reference_ID']+' | Downward candidate',font=font(22),fill='white')
        d.text((12,37),f"Native f{r['source_witnesses'][4]['frame0']} | draft",font=font(20),fill='#fbbf24')
        panel.paste(image,(25,70));panels.append(panel)
    sheet=Image.new('RGB',(1600,1730),'#111827');d=ImageDraw.Draw(sheet)
    d.text((15,7),'NEW CLIP: 12 assistant candidates; not the separate user-confirmed12 source clip',font=font(27),fill='white')
    d.text((15,43),'Representative native frames only; see full A/B triplets and raw5Hz clips. No model predictions.',font=font(23),fill='#fbbf24')
    for i,im in enumerate(panels):sheet.paste(im,((i%4)*400,80+(i//4)*550))
    dest=out/'twelve_draft_candidates_native_overview.jpg';sheet.save(dest,quality=95)
    # Empty acceptance template is deliberately not a ground-truth event file.
    acceptance={'status':'UNFILLED_INDEPENDENT_REVIEW_TEMPLATE_NOT_GROUND_TRUTH','source_filename':draft['source_filename'],
                'source_sha256':draft['source_sha256'],'assistant_draft_sha256':sha(src),'reviewer_role':None,
                'reviewer_independent_of_predictions':None,'new_clip_count_confirmed':None,'review_scope_windows_verified':False,
                'candidate_reviews':[{'reference_ID':r['reference_ID'],'accepted':None,'correct_direction':None,'correct_local_association':None,
                                       'final_event_frame0':None,'censor_or_ambiguity_note':None} for r in draft['candidates']],
                'additional_or_removed_events':[],'complete_event_list_accepted':False,'eligible_for_scoring':False,
                'template_contains_no_fabricated_human_confirmation':True}
    template=ROOT/'reference/independent_review_TEMPLATE.json';assert not template.exists();template.write_text(json.dumps(acceptance,indent=2),encoding='utf-8')
    text=['# 新长视频逐事件草案复核入口','',
          '2026-10-29。以下是新片2023-08-17T13-25-38.mp4的助理草案，共12个向下候选。**尚未经独立人工确认，不是此前用户已经确认12头的8912–10873片段。**',
          '', '图中为未经检测器绘框的原生像素，参考ID只供本次复核，不是注册牛只身份。', '',
          f'![12个候选的原生代表帧](<{dest.as_posix()}>)','',
          '| ID | 原生证据A三帧 | 原生证据B三帧 | 需细看时段（秒，原片名义时钟） | A/B证据图 |',
          '| --- | --- | --- | --- | --- |']
    for r in draft['candidates']:
        a='/'.join(map(str,r['origin_evidence_frame0']));b='/'.join(map(str,r['destination_evidence_frame0']));t=r['nominal_time_interval_s']
        text.append(f"| {r['reference_ID']} | {a} | {b} | {t[0]:.1f}–{t[1]:.1f} | [原生连续证据](<{(ROOT/r['witness_contact']).as_posix()}>) |")
    text+=['','时间栏是建议细看范围，不是已经确认的误差边界；精确完成帧仍为空。A/B证据展示上区与下区的三次观察，不能自动代替首次满足目标稳定条件的时间标注。',
           '', '对照原片时需核查：同一可见牛的关联、通道内完整通过、上下方向、躯干中心及首次目标区稳定时间；并排两牛保留两条，人员不计奶牛。也可增加遗漏候选、删除误列或标为歧义，不受草案数量约束。',
           '', '不带预测的5Hz通道回放：','',
           f"- [群体通行95–175秒](<{(ROOT/'focused_delivery/results/focused/group_passage/native_ROI_5hz.mp4').as_posix()}>)",
           f"- [单牛200–225秒](<{(ROOT/'focused_delivery/results/focused/late_single/native_ROI_5hz.mp4').as_posix()}>)",
           f"- [人员对照385–405秒](<{(ROOT/'focused_delivery/results/focused/person_control/native_ROI_5hz.mp4').as_posix()}>)",'',
           f"可填写[独立复核JSON模板](<{template.as_posix()}>)。空模板和助理草案均没有被当作人工真值；若只确认新片总数，也会按总数参考单独接受，不自动生成逐事件真值。",'',
           '片尾14056–14106帧保守隔离，不涉及这些窗口；参考绑定源帧号和原始SHA256。当前原片12头达标版本保持。']
    doc=ROOT/'逐事件草案复核入口.md';assert not doc.exists();doc.write_text('\n'.join(text)+'\n',encoding='utf-8')
    record={'status':'NATIVE_CANDIDATE_GUIDE_AND_EMPTY_INDEPENDENT_REVIEW_TEMPLATE_CREATED','draft_sha256':sha(src),
            'overview_path':str(dest),'overview_sha256':sha(dest),'template_sha256':sha(template),'guide_sha256':sha(doc),
            'candidate_panels':12,'human_acceptance_fabricated':False,'eligible_for_final_scoring':False}
    (out/'manifest.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record),flush=True)
if __name__=='__main__':main()
