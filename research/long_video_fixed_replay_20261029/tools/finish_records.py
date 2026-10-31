"""Record actual visual review and update the three live research entry points."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
def main():
    media=load(ROOT/'results/media_verification.json');case=load(ROOT/'results/case_diagnosis.json')
    notes={2640:'All trained models place native boxes on the leading cow; official has no current box.',
           2720:'seed26 shows three accumulated downward events; seed27 and seed28 four. Adjacent cows remain separate boxes.',
           2920:'All trained models cover the isolated patched cow; official has no current box.',
           3380:'Dark cow visible in each trained model; differing box centers and event timing are retained.',
           3605:'Three trained models cover the dark leading cow; following cow remains visible above.',
           3825:'Side-by-side cows remain visible. seed26 has one current box at this sample; seed27/28 two.',
           4005:'All trained models cover the final white-backed cow.',
           5320:'Three trained models show one late-window event and a box; official zero.',
           9900:'Person walking upward is visible; all four movies show zero local cow events.'}
    sheets=[]
    for row in media['case_sheets']:
        assert sha(Path(row['path']))==row['sha256']
        sheets.append({'path':row['path'],'sha256':row['sha256'],'source_frame0':row['source_frame0'],
                       'panels_viewed':4,'actual_visual_review':'PASS','observations':notes[row['source_frame0']]})
    for row in case['case_sheets']:
        assert sha(Path(row['path']))==row['sha256']
        sheets.append({**row,'panels_viewed':4,'actual_visual_review':'PASS',
                       'observations':'Native cow markings support continuity through the gap; raw boxes disappear for leading cow, then new confirmed ID23 appears below B. This is assistant case evidence, not independent GT.'})
    assert len(sheets)==11 and sum(r['panels_viewed'] for r in sheets)==44
    save(ROOT/'evidence/visual_review.json',{'status':'ELEVEN_SHEETS_FORTY_FOUR_PANELS_ACTUALLY_VIEWED',
         'recorded_UTC':datetime.now(timezone.utc).isoformat(),'sheets':sheets,
         'independent_human_reference_acceptance':False,'full_video_human_playback_claimed':False})
    link='<C:/Users/Donson/Documents/ChatGPT/奶牛/long_video_fixed_replay_20261029/普通俯视长片四模型回放与研究决策.md>'
    insertions={
      '研究进度.md':f'最新完成[普通俯视长片四模型实际回放]({link})：四个冻结checkpoint均从源帧0连续运行，共8100次前向、八条计数路径。当前交接链路向下预测为官方0／seed26为11／seed27与28各12；seed26存在ID19→23分段，seed27交接一次入口观察增加一事件。90交付条目、4808原始框逆变换、731中心和八路径独立复算通过；12视频12500帧完整解码，11张44面板目视。新片仍为助理待独立接受参考，不报正式准确率，原片人工12头达标版本保持。',
      '研究总览_从想法到论文.md':f'最新[普通俯视长视频四模型回放]({link})已实际完成：相同冻结输入与计数链路下，官方／seed26／seed27／seed28向下预测0／11／12／12，全部模型和两个计数器对照保留。原生病例定位了检测缺口后的轨迹分段，以及确认前一次观察交接带来的事件增量；12个视频与独立复算已核查。新片尚无独立接受的参考，不能把12预测写成100%准确率；原源片人工确认12头的seed26达标成果继续保留。后续按错误证据推进新会话参考、关联或训练对照、身份触发及PYNQ-Z2联合实测。',
      'phase3_diagnosis_20261026/方案与执行状态.md':f'新增完成[普通俯视长片固定四模型／八计数路径回放]({link})：8100前向、同一源帧0历史，当前向下预测0／11／12／12；确认后对照0／11／11／12。seed26轨迹分段与seed27入口交接病例已核查，90条目、八路径独立复算、12500视频帧及44面板核查通过。该新片现列开发诊断，参考草案保持待独立接受；不计算正式F1，不改原片12头达标模型，后续继续普通俯视、真实双向、身份及板上联合链路。'}
    for name,paragraph in insertions.items():
        path=PROJECT/name;text=path.read_text(encoding='utf-8');assert 'long_video_fixed_replay_20261029' not in text
        parts=text.split('\n\n',2);assert len(parts)==3 and parts[0].startswith('# ') and '更新' in parts[1]
        text=parts[0]+'\n\n'+parts[1]+'\n\n'+paragraph+'\n\n以下按阶段保留此前记录；当时“尚未回放”等表述是历史状态，本轮实际结果以上述报告为准。\n\n'+parts[2]
        path.write_text(text,encoding='utf-8')
    plan=ROOT/'计划与验收.md'
    text=plan.read_text(encoding='utf-8');assert '执行结果：' not in text
    text+='\n执行结果：Slurm130345已COMPLETED／0:0，用时9分14秒。四模型8100前向、八路径独立复算、90交付条目和12视频12500帧检查已完成；11张44面板已目视。当前交接预测0／11／12／12，正式参考评分未执行。完整结果和后续顺序见[本轮报告](<C:/Users/Donson/Documents/ChatGPT/奶牛/long_video_fixed_replay_20261029/普通俯视长片四模型回放与研究决策.md>)。\n'
    plan.write_text(text,encoding='utf-8')
    print(json.dumps({'visual_sheets':11,'visual_panels':44,'live_entry_points_updated':3,'reference_or_model_changed':False}))
if __name__=='__main__':main()
