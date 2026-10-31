from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    media=load(ROOT/'results/media_verification.json');focus=load(ROOT/'results/failure_focus_record.json')
    rows=[]
    for case in media['case_sheets']:
        path=ROOT/'media_delivery'/case['path'];assert sha(path)==case['sha256']
        name,frame=case['source'],case['frame0']
        if name=='long_official':note='Native cows visible with no current confirmed boxes; zero events in both variants.'
        elif name=='long_seed26':note='Same pixels show candidate recovery and extra accumulated event; at3825 candidate also has a current box for the right cow while original has only the left current box.'
        elif name in ['long_seed27','long_seed28']:note='Both visible cows remain separately boxed at preset anchors; counts agree locally while numeric IDs may differ.'
        elif name.startswith('original_'):
            note='Same original native passage pixels and displayed counts agree. Current boxes and numeric IDs may differ; overlap is not alone physical duplicate proof.'
            if name=='original_seed26' and frame==10415:note+=' Nearly coincident boxes are visible over the foreground cow; ledger retains both variants.'
            if name=='original_seed27' and frame==9345:note+=' Candidate has an additional middle-cow box at this anchor.'
        elif name=='toros_generic':
            note='Publisher14 blue and7 pink remain visibly separate reference cows. Prediction green supports source-linked ID5 change, counts later6versus5;193has no current green confirmed box.'
        else:note='Reverse cattle source visible; current predictions and cumulative counts differ. High-overlap candidate frames are retained for inspection.'
        rows.append({**case,'absolute_path':str(path.resolve()),'actual_visual_review':'PASS','observations':note})
    assert len(rows)==31 and sum(r['panels'] for r in rows)==62
    assert sum(r['predefined_anchor'] for r in rows)==22
    assert sha(Path(focus['figure_path']))==focus['figure_sha256']
    record={'status':'31_PAIRED_SHEETS_PLUS_READABLE_FOUR_PANEL_FIGURE_ACTUALLY_VIEWED',
            'created_UTC':datetime.now(timezone.utc).isoformat(),'sheets':rows,
            'failure_focus_figure':{'path':focus['figure_path'],'sha256':focus['figure_sha256'],'panels':4,'actual_visual_review':'PASS',
              'observations':'Readable crop confirms both variantsID5cover publisher14 at153; at167 originalID5covers14 and candidateID5covers7. Source crop, legend, layout and labels checked.'},
            'actual_sheets_viewed':32,'actual_panels_viewed':66,'independent_new_reference_acceptance':False,
            'all_movie_frames_human_viewed_claimed':False}
    out=ROOT/'evidence/visual_review.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    link='<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/多seed与反向回归结果及采用决策.md>'
    paragraphs={
      '研究进度.md':f'最新完成[第一阶段纯IoU多seed／原片／反向回归]({link})：9份缓存、18跟踪、31166更新及36计数路径全部保留，9原基线先精确回归。新长片seed26预测11→12，原片三seed仍12／11／11；但Toros官方正确匹配6→5、旧五轮2→4。官方ID5转跟邻牛的发布方框支持已核查，重叠候选增加，故不作全局替换，原12头达标版本保持。36路径、9027中心、6367框对、8评分及病例175IoU独立复算；9视频8444帧完整解码，32图66面板目视。新长片参考仍待独立接受，身份与PYNQ-Z2联合主线继续。',
      '研究总览_从想法到论文.md':f'最新[第一阶段候选的完整回归与采用决策]({link})支持保留当前基线：局部普通俯视恢复重现，但Toros官方6次正确匹配降为5次；原片人工12头成功总数保持。已完成9缓存／18跟踪／36计数路径、多seed、全部不利结果及发布方身份对应病例核查，未临时添加场景或seed特判。候选保存作机制控制，不作全局替换，也不认领新颖算法贡献。独立计数／代价、9并排视频和失败放大图可查；后续继续可信事件参考、事件抓拍与异常身份查询，以及PYNQ-Z2前后台联合实测。',
      'phase3_diagnosis_20261026/方案与执行状态.md':f'后续已完成[第一阶段纯IoU候选多条件回归]({link})：9原基线精确复现后跑9候选，共36计数路径；原片人工12头三seed总数保持，新长片seed26为11→12，但Toros官方参考匹配6→5，旧五轮2→4。发布方ID14／7对应变化和重叠风险保留，当前不采用全局替换。9027中心、6367框对、8评分、9媒体8444帧和32图66面板核查完成；原12头成功版本、新片参考及此前实验保持，后续身份链路和板上验证仍按原目标推进。'}
    for name,paragraph in paragraphs.items():
        path=PROJECT/name;old=path.read_text(encoding='utf-8');assert 'firststage_iou_regression_20261029' not in old
        parts=old.split('\n\n',2);assert len(parts)==3 and parts[0].startswith('# ') and '更新' in parts[1]
        path.write_text(parts[0]+'\n\n'+parts[1]+'\n\n'+paragraph+'\n\n'+parts[2],encoding='utf-8')
    plan=ROOT/'计划与验收.md';text=plan.read_text(encoding='utf-8');assert '执行结果：' not in text
    text+='\n执行结果：130351回归与130352媒体均COMPLETED／0:0；9原基线精确回归、18条件36路径和全部对照已完成。新片seed26为11→12、原片12／11／11保持，Toros官方6→5、旧五轮2→4；不作全局替换。独立9027中心／6367框对／8评分、175病例IoU、9媒体8444帧及32图66面板核查完成。详见[结果与采用决策](<C:/Users/Donson/Documents/ChatGPT/奶牛/firststage_iou_regression_20261029/多seed与反向回归结果及采用决策.md>)，完整研究目标继续。\n'
    plan.write_text(text,encoding='utf-8')
    print(json.dumps({'actual_sheets_viewed':32,'actual_panels_viewed':66,'research_entries_updated':3,'candidate_adopted':False}))
if __name__=='__main__':main()
