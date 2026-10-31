from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
for phase in ['mosaic_event_diagnosis_20261030','unconfirmed_iou_20261030']:
    final=load(PROJECT/phase/'results/final_review.json');assert not final['whole_goal_complete']
    for row in final['documents']:assert sha(row['path'])==row['sha256']
overview=PROJECT/'研究阶段总结_20261030.md';old=load(PROJECT/'research_synthesis_20261027/results/overview_review_20261030_v5.json')
assert sha(overview)==old['document']['sha256']
latest='''最新完成[新旧O8的11／10差异诊断](<C:/Users/Donson/Documents/ChatGPT/奶牛/mosaic_event_diagnosis_20261030/新旧O8计数差异与确认瓶颈.md>)与[仅未确认阶段纯IoU的111缓存控制](<C:/Users/Donson/Documents/ChatGPT/奶牛/unconfirmed_iou_20261030/未确认关联控制与不采用决定.md>)：开发参照103原始入口3次，确认与合法交接仅2次；9550实际融合代价0.772超过0.7门限。只换该处代价即可在服务器重放中10→11，但全程控制使新O8的30Hz反向4→3、新FP32的5Hz3→2，故不采用全局改动。111基线先复现，444计数路径／238配对范围、原64012和官方Toros6均保留；单帧处理仅诊断，非部署规则。本轮没有新增网络或板端效果，真实板端新模型计数仍10／人工12，下一步继续普通俯视独立参考、连续检测与因果抓拍质量。'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
snapshot=ROOT/'evidence/entrypoints_before';snapshot.mkdir(exist_ok=False);updates=[]
for i,p in enumerate(paths):
    text=p.read_text(encoding='utf-8');before=sha(p);backup=snapshot/(str(i)+'_'+p.name);backup.write_bytes(p.read_bytes())
    mark='最新完成固定mosaic0.5主seed26'
    assert text.count(mark)==1;text=text.replace(mark,latest+'\n\n前一实机阶段：固定mosaic0.5主seed26',1)
    if p==overview:
        mark='后台照片还暴露出另一问题：'
        extra='''新旧实际O8差异已进一步定位：开发参照103的实际原始框有3次连续入口观察，确认及合法交接只留下2次。9550分数0.28858足够进入高分集合，但融合代价即使IoU=1也至少0.7114，超过未确认阶段0.7门限；实测融合0.7722、纯IoU0.2105。只在9550干预就能恢复对应通行，但全局改纯IoU有回归，故不采用。94的入口检测缺口与103的确认损失分别保留；640模型参照仍不是人工真值。[确认瓶颈与单因素回归](<C:/Users/Donson/Documents/ChatGPT/奶牛/unconfirmed_iou_20261030/未确认关联控制与不采用决定.md>)

'''
        assert text.count(mark)==1;text=text.replace(mark,extra+mark)
        old='2. 新主候选PTQ、2654实际O8视频与两轮周期负载已完成。反向3／6已是真实板端结果，但原片10比旧11退步，暂不默认替换。继续定位两种模型的完整通行差异，并在普通俯视新会话及独立参考上比较，不通过换seed或加源片训练来追12。'
        new='2. 新旧实际通行差异及确认阶段单因素控制已完成，局部恢复1次但全局有回归，继续保留原规则。94的连续入口检测与103的确认损失分别验证，结合普通俯视新会话及独立参考，不通过换seed、帧号特判或向训练加入原片来追12。'
        assert text.count(old)==1;text=text.replace(old,new)
        old='最新实验结束后已重新读取3个新父任务和4个身份子任务，均正常终态且PID消失，SSH与Jupyter可访问、共享加速锁空闲且原O8 bit保持。没有更改全局运行环境或自动全局替换模型。'
        new='前一实机阶段结束时已读取3个父任务和4个身份子任务，均正常终态且PID消失，并记录SSH／Jupyter及O8状态。本轮只读缓存与运行服务器CPU控制，没有新增板端时序或连接状态测量；全局运行环境、跟踪源码与默认模型未替换。'
        assert text.count(old)==1;text=text.replace(old,new)
    p.write_text(text,encoding='utf-8');updates.append({'path':str(p),'before_sha256':before,'after_sha256':sha(p),'before_snapshot':str(backup)})
f=ROOT/'results/entrypoint_updates.json';assert not f.exists();f.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates,'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'updated':4,'production_change':False,'whole_goal_complete':False}))
