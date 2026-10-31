from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    media=load(ROOT/'results/paired_media_verification.json')
    notes={2645:'Same source leading cow is covered by ID19 in both full-history variants before the gap.',
           2655:'Leading cow remains visible with no current box in both variants; following cowID20 has a box. No predicted-only observation is drawn.',
           2665:'Candidate recovers ID19 on the leading cow while original has no current leading-cow confirmed box. Candidate score shown is0.31.',
           2670:'Original leading cow isID23 while candidate keepsID19; adjacent following and rear cows remain visible.',
           2675:'Original window count0 versus candidate1; ID19 in candidate remains on the source-supported leading cow.',
           3840:'Counts differ temporarily by2 because the candidate has the extra earlier event and a second event advanced by0.2s; temporary IDs differ.'}
    rows=[]
    for row in media['contacts']:
        assert sha(Path(row['path']))==row['sha256']
        rows.append({**row,'actual_visual_review':'PASS','observations':notes[row['frame0']]})
    out=ROOT/'evidence/visual_review.json';assert not out.exists()
    out.write_text(json.dumps({'status':'SIX_PAIRED_CASE_SHEETS_TWELVE_PANELS_ACTUALLY_VIEWED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'sheets':rows,'physical_correspondence_authority':'assistant_post_prediction_case_review',
        'independent_reference_acceptance':False,'browser_full_playback_claimed':False},indent=2)+'\n',encoding='utf-8')
    link='<C:/Users/Donson/Documents/ChatGPT/奶牛/long_video_track_gap_20261029/新片轨迹分段定位与单因素对照.md>'
    texts={
      '研究进度.md':f'继续完成[新长片轨迹分段定位与第一阶段单因素控制]({link})：全2025更新精确复现；六步短信号两次稳定复现原ID未恢复。插桩排除ROI及轨迹过期，51代价项与26部分分配独立核对。仅把第一阶段代价改为纯IoU后，同一快照恢复ID19并在2675发事件，完整新片seed26预测11→12；另一个事件3845→3840及ID重编号保留。四路径／600中心复算、625源图哈希、三媒体625帧及六张12面板核查完成。候选未替换原片人工12头达标版本，其他seed／旧片回归和新片独立事件参考继续待验。',
      '研究总览_从想法到论文.md':f'最新[普通俯视长片关联机制实验]({link})在相同检测框下取得seed26预测11→12：从同一中断前状态恢复了原ID，3次真实B区观察后发出事件。只改变第一阶段的分数融合，原模型、输入、第二阶段、确认和计数规则保持。独立数值、事件和并排媒体核查完成；另一事件提前0.2秒等变化全部保留。这支持先做关联回归，尚不构成新片100%准确率、最终采用或论文贡献；原片人工12头成功版本保持，下一步核查其他seed、原片与真实反向片。',
      'phase3_diagnosis_20261026/方案与执行状态.md':f'新增完成[新长片关联边界与单因素控制]({link})：原ID19始终留在第一阶段池，检测缺口后重现框的融合代价超过门槛，ROI与过期解释被排除。六步同状态控制将恢复信号从红变绿，整片seed26的两计数路径均11→12；其余输出变化保留。51矩阵项、26分配、四路径、三视频625帧和12面板核查完成。候选不替换原片12头达标组合，后续先做其他seed与旧片回归，再决定采用和训练。'}
    for name,text in texts.items():
        path=PROJECT/name;old=path.read_text(encoding='utf-8');assert 'long_video_track_gap_20261029' not in old
        parts=old.split('\n\n',2);assert parts[0].startswith('# ') and '更新' in parts[1]
        path.write_text(parts[0]+'\n\n'+parts[1]+'\n\n'+text+'\n\n'+parts[2],encoding='utf-8')
    path=ROOT/'计划与验收.md';old=path.read_text(encoding='utf-8');assert '执行结果：' not in old
    old+='\n执行结果：原基线与插桩全历史精确回归；第一阶段单因素协议已先行冻结并真实执行。同一快照的六步控制恢复ID19且2675发事件；整片两计数路径均11→12，另一事件提前0.2秒及ID变化保留。三个CPU作业130347／130348／130349均COMPLETED／0:0。独立51矩阵项／26分配、四计数路径／600中心及三视频625帧核查完成；原12头版本未改，候选尚待其他seed／旧片回归及新片参考接受。见[本轮报告](<C:/Users/Donson/Documents/ChatGPT/奶牛/long_video_track_gap_20261029/新片轨迹分段定位与单因素对照.md>)。\n'
    path.write_text(old,encoding='utf-8')
    print(json.dumps({'actual_visual_sheets':6,'actual_visual_panels':12,'live_research_entries_updated':3,'candidate_adopted':False}))
if __name__=='__main__':main()
