from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
review=load(ROOT/'results/final_review.json');assert review['whole_goal_complete'] is False
for row in review['documents']:assert sha(Path(row['path']))==row['sha256']
overview=PROJECT/'研究阶段总结_20261030.md'
old_review=load(PROJECT/'research_synthesis_20261027/results/overview_review_20261030_v2.json')
assert sha(overview)==old_review['document']['sha256']
latest='''最新质量对照：[固定192亮度／对比度结果与训练决策](<C:/Users/Donson/Documents/ChatGPT/奶牛/photometric_input_20261030/输入亮度对照结果与训练决策.md>)已完成25350次FP32／QDQ推理、36计数路径和3图34面板复核。gamma0.7静态匹配增加11／9，原片计数却由10／11降至8／10；CLAHE均为8，两个变换不采用。剩余暗色案例入口最长仍不足3次稳定观察；下一步审计普通俯视训练样本覆盖并做配对训练。本轮没有新增板端动作，历史O8原输入11／人工12及约5FPS同板记录保持。'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
updates=[];snapshot=ROOT/'evidence/entrypoints_before';snapshot.mkdir(exist_ok=False)
for i,path in enumerate(paths):
    text=path.read_text(encoding='utf-8');before=sha(path)
    (snapshot/(str(i)+'_'+path.name)).write_bytes(path.read_bytes())
    if path==overview:
        anchor='## 1. 两个方向可以这样定义'
        assert text.count(anchor)==1
        text=text.replace(anchor,latest+'\n\n'+anchor)
        old='下一步优先普通俯视暗色／遮挡正例和事先冻结的输入／训练控制'
        assert text.count(old)==1;text=text.replace(old,'下一步优先普通俯视暗色／遮挡正例和事先冻结的训练控制')
        mark='后台照片还暴露出另一问题：'
        addition='''已完成的gamma0.7和CLAHE输入对照未改善完整计数。CLAHE在该局部参照的IoU0.3对应增多，但入口最长只有两次，仍不足三次稳定要求；不能只展示局部框增多。全部36计数路径、12675个源输入hash和34图像面板已核查。Toros在这里是侧视反向压力对照，后续训练仍按用户要求使用普通俯视材料。[输入对照自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/photometric_input_20261030/Review与当前状态.md>)

'''
        assert text.count(mark)==1;text=text.replace(mark,addition+mark)
        old='2. 冻结低分辨率暗色／遮挡案例的输入或训练对照，使用全部事件与负例评价；同时检查Toros跨来源退化，不在Toros上训练后仍称其独立测试。'
        new='2. 先审计训练集本身的暗色／遮挡和有效牛体像素覆盖，再固定低分辨率配对训练；输入亮度对照已完成且未采用。使用全部事件与负例评价，同时保留Toros跨来源压力结果，不在Toros上训练后仍称其独立测试。'
        assert text.count(old)==1;text=text.replace(old,new)
    else:
        assert text.count('当前统一入口：')==1;text=text.replace('当前统一入口：',latest+'\n\n当前统一入口：',1)
    path.write_text(text,encoding='utf-8')
    updates.append({'path':str(path),'before_sha256':before,'after_sha256':sha(path),'before_snapshot':str(snapshot/(str(i)+'_'+path.name))})
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'phase_final_review_sha256':sha(ROOT/'results/final_review.json'),'updates':updates,
    'overview_prior_manual_review_sha256':sha(PROJECT/'research_synthesis_20261027/results/overview_review_20261030_v2.json'),'whole_goal_complete':False}
p=ROOT/'results/entrypoint_updates.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'updated':len(updates),'whole_goal_complete':False}))
