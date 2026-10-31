from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OUT=ROOT/'delivery/results/control_v2'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def link(p,label):return '['+label+'](<'+str(Path(p).resolve()).replace('\\','/')+'>)'
s=load(OUT/'summary.json');v=load(ROOT/'results/independent_verification.json');causal=load(ROOT/'results/one_frame_independent_verification.json')
appendix=load(ROOT/'results/native_Toros_score_appendix.json');pairs=load(OUT/'paired_metrics.json')
assert s['counter_paths']==444 and v['counter_observation_ticks']==217078 and causal['diagnostic_count']==11
def row(cache):return next(r for r in pairs if r['cache']==cache and r['counter']=='handoff_events')
table=[]
for label,cache in [('旧实际O8','old_O8'),('新FP32 ONNX','new_FP32'),('新QDQ ONNX','new_QDQ'),('新实际O8缓存','new_O8')]:
    a=row(cache+'_original_s5');b=row(cache+'_toros_s6');c=row(cache+'_toros_s1')
    table.append('| '+label+' | '+str(a['baseline_down'])+' → '+str(a['control_down'])+' | '+str(b['baseline_TP_FP_FN'][0])+' → '+str(b['control_TP_FP_FN'][0])+' | '+str(c['baseline_TP_FP_FN'][0])+' → '+str(c['control_TP_FP_FN'][0])+' |')
text=f'''# 未确认阶段纯IoU：局部恢复1次，完整回归不支持全局采用

2026年10月30日。**不把本轮控制设为默认跟踪规则。** 在固定新O8原始输出上，仅未确认阶段关闭分数融合，原片计数10→11，5Hz反向仍3／6；但30Hz控制4→3，新FP32的5Hz反向3→2，其他模型也有计数下降。局部瓶颈已经通过实际代价和单帧诊断确认，不能把该结论扩大成纯IoU全面更好。

本轮只在服务器重放缓存，不新增YOLO或身份前向，不改任何板上程序。既有新模型实际周期计数仍为10；这里的11是**基于真实O8 raw的服务器跟踪控制**，不是改后系统已上板或已经达到12。

## 唯一干预与原始瓶颈

保持检测conf0.2、track high0.25、low0.1、new0.25、未确认阶段代价门限0.7、第一／第二关联、三次稳定和入口交接。实验子类只在`_unconfirmed_association`调用范围临时设fuse_score=False，返回或异常后恢复；原始ByteTrack源码没有改动。

9550帧的目标检测分数0.28858277，纯IoU代价0.21052730，置信度融合后为0.77217180，超过0.7。代价公式为`1-IoU×score`；即使IoU=1，也至少0.71141723。原暂定25无法确认而被丢弃；全程控制中的暂定编号为23，成功确认后补入9545观察，恢复三次入口稳定证据。

编号不同是轨迹分配顺序变化，不是不同永久牛号。恢复的通行在9605帧发生，与旧640开发参照103的一对一最优空间对应IoU约0.7212；开发参照不是人工GT。

## 单帧诊断：确认该处的局部因果作用

另外只在9550这个调用换代价，所有其他帧保持原融合。9550之前全部观察、框和两条事件列表精确相同，暂定25在9550被确认，原片10→11，9605出现上述对应事件。2175个时刻及两条计数路径已独立复算。

这是从已观察失败点选取的诊断干预，不是可上线的帧号特判，也没有把它作为独立测试或论文通用方法。完整控制仍然必须面对下面的不利结果。

## 全部111缓存后再决定采用

先复现90条新低分辨率全图／裁剪缓存、旧实际O8和新FP32／QDQ／实际O8的12采样路径，以及9个历史原生来源，共111缓存；然后才运行控制。它们复用已看过的视频和权重，不能写成111个独立牧场会话。

以下均为入口交接路径，单元格为原融合→仅未确认阶段纯IoU。Toros数字是发布方6事件中的正确匹配，表中FP均0，FN为6减TP；30Hz是源采样控制，不是板端FPS。

| 固定raw来源 | 原片计数／人工12 | Toros5Hz TP／6 | Toros30Hz TP／6 |
| --- | --- | --- | --- |
{chr(10).join(table)}

既有640原片12头版本保持12→12；对应seed27为11→12、seed28为11→11。官方Toros为6／0／0保持，旧五轮模型2／0／4保持。长片四模型的person_control都仍为0，也没有把未接收的长片草案当正式事件成绩。

其他不利例子包括：旧192直角seed26裁剪FP32的10→8、320直角seed26的12→11、某192普通模型的5Hz反向1→0。两条计数路径和全部窗口共有238配对范围、38行数量变化；这一分母是模型／窗口条件，不是238次独立真实通行。所有seed及不利结果见{link(OUT/'paired_metrics.json','238行完整配对表')}。

## 回放顺序、失败与记录恢复

130637在91条基线已经复现、控制尚未开始时因板端Toros临时ID列表不同而失败。130638完成六个诊断记录后在打印摘要时TypeError退出，已保存的诊断完整取回，没有重跑这些记录。

定位发现原实际视频程序同时创建5Hz与30Hz两套跟踪器，按每个源帧先5Hz、再30Hz交错更新，共享STrack的全局ID分配计数。孤立回放每条路径会改变ID标签，空间和事件时刻却相同。v2精确复现原交错顺序，ID／事件仍严格相等；没有重新编号“配齐”、忽略ID或放宽容差。CPU缓存按原约定严格复现，真实ARM坐标仍用此前已固定的0.002像素／2e-6轴坐标门限。

91份通过的基线及失败输出原样保留并复用，未重复其跟踪计算。130639完成／0:0、45秒，实际共222个跟踪条件、217078个含前史时刻、444条计数路径，另有476个窗口指标（长片多窗口）。111个基线门禁全部通过后才进入控制分支。

原生Toros来源的scene别名为toros_used_reverse，初始构造器只在scene=toros时关联参考，因此原指标的两来源formal字段为None。保留原476行，另以此前同一6事件参考追加8个评分条件，没有改raw／轨迹／计数、阈值或重跑；{link(ROOT/'results/native_Toros_score_appendix.json','评分关联修正与原始None记录')}单列时间范围，不伪装事前已完成。

## 独立复算与研究决定

独立重算444条计数路径、217078个时刻、476窗口指标、272个原评分条件、106415条确认框／中心、238配对范围及9550实际矩阵。单帧诊断另复算两条路径；所有原始数据、90缓存源码和工作区均未修改。前置只读诊断的3源帧／9面板也已查看，见{link(PROJECT/'mosaic_event_diagnosis_20261030/新旧O8计数差异与确认瓶颈.md','新旧模型差异诊断')}。

完整结果包9,765,448字节，SHA `0b7878348ab14011805b6b6803b99b3fab20db02647be409943bf0cb52ea577c`，650文件；单帧诊断包35,938字节，SHA `82021279a4da7ba0041ed1d64dd34145385ec37d433eb2daaf4b395de868a07b`，均本地逐文件校验。

本轮确认了新模型额外少计的一处机制，也证明直接全局改纯IoU有代价。保持现有板端默认规则；下一步优先独立通行参考和普通俯视新会话，再将确认风险、连续检测与因果抓拍质量分别验证。原片仍未达到人工12头，永久身份与实际耳标参考也不足，不宣布整体目标完成。

{link(ROOT/'results/independent_verification.json','完整独立复算')} · {link(ROOT/'results/one_frame_independent_verification.json','单帧诊断复算')} · {link(ROOT/'protocol/control_v2.json','冻结协议及111缓存')} · {link(ROOT/'tools/confirmation_iou.py','独立实验子类')}
'''
f=ROOT/'未确认关联控制与不采用决定.md';assert not f.exists();f.write_text(text,encoding='utf-8')
review='''# 未确认关联控制Review与当前状态

- 所有111基线先通过，再跑控制；91份通过的旧基线未重复计算且哈希保持。
- 两个失败与共享ID分配的原采样顺序单列；没有重新编号或放宽ID／事件门禁。
- 217078观察、444计数路径与238配对范围独立复算，不把缓存条件当独立动物样本。
- 局部10→11与反向／其他模型退步均保留，全局规则不采用；服务器重放不称实际改后上板。
- 单帧9550仅诊断，不作生产特判；前面状态精确相同，局部恢复事件仍只对应开发参照。
- 原生Toros元数据别名修正追加8评分，原None和原476指标不覆盖。
- IMPORTANT：没有新增板上时序或身份准确率，检测框、临时ID、永久牛号保持区分。
- BLOCKER：人审逐事件／永久身份及真实双向普通俯视数据待补，整体目标继续。
'''
f=ROOT/'Review与当前状态.md';assert not f.exists();f.write_text(review,encoding='utf-8')
print(json.dumps({'report':str(ROOT/'未确认关联控制与不采用决定.md'),'counter_paths':444,'single_frame_extra_paths':2,'adopted_for_deployment':False,'whole_goal_complete':False}))
